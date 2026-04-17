"""Log Analyzer CDK Stack — provisions all AWS resources for the serverless deployment."""

import json
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_dynamodb as ddb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lmb
from aws_cdk import aws_logs as cwlogs
from aws_cdk import aws_logs_destinations as cwlogs_dest
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct

_ROOT = Path(__file__).resolve().parent
_CODE_PATH = str(_ROOT / "lambda_code")
_LAYER_PATH = str(_ROOT / "lambda_layer")
_DASH_PATH = str(_ROOT / "dashboard")


class LogAnalyzerStack(Stack):
    """Provisions DynamoDB, Lambda functions, API Gateway, and S3 dashboard."""

    def __init__(self, scope: Construct, cid: str, **kwargs) -> None:
        super().__init__(scope, cid, **kwargs)

        cdk.Tags.of(self).add("owner", "ariel.sisro@endava.com")
        cdk.Tags.of(self).add("project", "AI Functions investigation project")

        tbl_env = self._provision_tables()
        layer = self._build_layer()
        br_policy = self._bedrock_policy()

        proc = self._processor_lambda(tbl_env, layer, br_policy)
        api_fn = self._api_lambda(tbl_env, layer, br_policy)
        gw = self._rest_api(api_fn)
        dash_url = self._dashboard(gw.url)
        self._cw_subscriptions(proc)
        gen = self._test_generator_lambda(proc)

        CfnOutput(self, "ApiGatewayUrl", value=gw.url)
        CfnOutput(self, "DashboardSiteUrl", value=dash_url)
        CfnOutput(self, "ProcessorFnName", value=proc.function_name)
        CfnOutput(self, "ApiFnName", value=api_fn.function_name)
        CfnOutput(self, "TestGenFnName", value=gen.function_name)

    def _provision_tables(self) -> dict[str, str]:
        """Create DynamoDB tables with GSIs for the logs table."""
        self._logs_tbl = ddb.Table(
            self, "AnalyzedLogsTable",
            table_name="log-analyzer-logs",
            partition_key=ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self._logs_tbl.add_global_secondary_index(
            index_name="gsi-level-time",
            partition_key=ddb.Attribute(name="log_level", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="created_at", type=ddb.AttributeType.STRING),
        )
        self._logs_tbl.add_global_secondary_index(
            index_name="gsi-category-time",
            partition_key=ddb.Attribute(name="category", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="created_at", type=ddb.AttributeType.STRING),
        )
        self._incidents_tbl = ddb.Table(
            self, "IncidentReportsTable",
            table_name="log-analyzer-incidents",
            partition_key=ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        return {
            "LOGS_TABLE": self._logs_tbl.table_name,
            "INCIDENTS_TABLE": self._incidents_tbl.table_name,
        }

    def _build_layer(self) -> lmb.LayerVersion:
        """Lambda layer with shared dependencies (ai_functions + pydantic)."""
        return lmb.LayerVersion(
            self, "AiFuncsDepsLayer",
            code=lmb.Code.from_asset(_LAYER_PATH),
            compatible_runtimes=[lmb.Runtime.PYTHON_3_12],
            description="Shared deps: ai_functions and pydantic for log analyzer",
        )

    @staticmethod
    def _bedrock_policy() -> iam.PolicyStatement:
        """IAM statement granting Bedrock model invocation."""
        return iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["*"],
        )

    def _processor_lambda(self, env_vars, layer, br_stmt) -> lmb.Function:
        """CloudWatch log processor — receives subscription events, runs AI pipeline."""
        fn = lmb.Function(
            self, "CWProcessorFn",
            function_name="log-analyzer-cw-processor",
            runtime=lmb.Runtime.PYTHON_3_12,
            handler="cloudwatch_handler.handler",
            code=lmb.Code.from_asset(_CODE_PATH),
            timeout=Duration.minutes(5),
            memory_size=512,
            layers=[layer],
            environment=env_vars,
        )
        fn.add_to_role_policy(br_stmt)
        self._logs_tbl.grant_read_write_data(fn)
        self._incidents_tbl.grant_read_write_data(fn)
        return fn

    def _api_lambda(self, env_vars, layer, br_stmt) -> lmb.Function:
        """REST API handler — serves dashboard queries and on-demand analysis."""
        fn = lmb.Function(
            self, "RestApiFn",
            function_name="log-analyzer-api",
            runtime=lmb.Runtime.PYTHON_3_12,
            handler="api_handler.handler",
            code=lmb.Code.from_asset(_CODE_PATH),
            timeout=Duration.minutes(5),
            memory_size=512,
            layers=[layer],
            environment=env_vars,
        )
        fn.add_to_role_policy(br_stmt)
        self._logs_tbl.grant_read_write_data(fn)
        self._incidents_tbl.grant_read_write_data(fn)
        return fn

    def _rest_api(self, api_fn: lmb.Function) -> apigw.RestApi:
        """API Gateway REST API with CORS — routes to the API Lambda."""
        gw = apigw.RestApi(
            self, "LogAnalyzerGateway",
            rest_api_name="LogAnalyzerGateway",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )
        integration = apigw.LambdaIntegration(api_fn)
        api_root = gw.root.add_resource("api")

        logs_res = api_root.add_resource("logs")
        logs_res.add_method("GET", integration)
        logs_res.add_method("DELETE", integration)

        stats_res = api_root.add_resource("stats")
        stats_res.add_method("GET", integration)

        analyze_res = api_root.add_resource("analyze")
        analyze_res.add_method("POST", integration)

        correlate_res = api_root.add_resource("correlate")
        correlate_res.add_method("POST", integration)

        incidents_res = api_root.add_resource("incidents")
        incidents_res.add_method("GET", integration)
        return gw

    def _dashboard(self, api_gw_url: str) -> str:
        """Private S3 bucket + CloudFront distribution for the dashboard."""
        bucket = s3.Bucket(
            self, "DashboardSiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        distribution = cloudfront.Distribution(
            self, "DashboardCDN",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
            ],
        )

        s3deploy.BucketDeployment(
            self, "DashboardAssets",
            sources=[s3deploy.Source.asset(_DASH_PATH)],
            destination_bucket=bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )
        return f"https://{distribution.distribution_domain_name}"

    def _cw_subscriptions(self, processor_fn: lmb.Function) -> None:
        """Subscribe external CloudWatch log groups to the processor (optional via CDK context)."""
        raw_ctx = self.node.try_get_context("log_group_names")
        if not raw_ctx:
            return
        names = json.loads(raw_ctx) if isinstance(raw_ctx, str) else raw_ctx
        for idx, lg_name in enumerate(names):
            ext_lg = cwlogs.LogGroup.from_log_group_name(self, f"ExtLG{idx}", lg_name)
            cwlogs.SubscriptionFilter(
                self, f"ExtSub{idx}",
                log_group=ext_lg,
                destination=cwlogs_dest.LambdaDestination(processor_fn),
                filter_pattern=cwlogs.FilterPattern.all_events(),
            )

    def _test_generator_lambda(self, processor_fn: lmb.Function) -> lmb.Function:
        """Test log generator — emits sample logs that trigger the processor."""
        gen_log_group = cwlogs.LogGroup(
            self, "TestGenLogGroup",
            log_group_name="/aws/lambda/log-analyzer-test-generator",
            removal_policy=RemovalPolicy.DESTROY,
            retention=cwlogs.RetentionDays.ONE_WEEK,
        )
        gen_fn = lmb.Function(
            self, "TestGenFn",
            function_name="log-analyzer-test-generator",
            runtime=lmb.Runtime.PYTHON_3_12,
            handler="test_log_generator.handler",
            code=lmb.Code.from_asset(_CODE_PATH),
            timeout=Duration.seconds(30),
            memory_size=128,
            log_group=gen_log_group,
        )
        cwlogs.SubscriptionFilter(
            self, "TestGenProcessorSub",
            log_group=gen_log_group,
            destination=cwlogs_dest.LambdaDestination(processor_fn),
            filter_pattern=cwlogs.FilterPattern.all_events(),
        )
        return gen_fn
