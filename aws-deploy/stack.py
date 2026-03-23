"""CDK Stack — Log Analyzer on AWS.

Provisions: DynamoDB tables, Lambda functions, API Gateway, S3 dashboard,
and optional CloudWatch subscription filters for automatic log processing.
"""
from __future__ import annotations

import json as _json
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Duration, RemovalPolicy, CfnOutput
from aws_cdk import aws_dynamodb as ddb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lmb
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_logs as cwlogs
from aws_cdk import aws_logs_destinations as cwdest
from constructs import Construct

_ROOT = Path(__file__).resolve().parent


class LogAnalyzerStack(cdk.Stack):
    """Full infrastructure for the AI-powered log analyzer."""

    def __init__(self, scope: Construct, cid: str, **kwargs) -> None:
        super().__init__(scope, cid, **kwargs)

        cdk.Tags.of(self).add("owner", "ariel.sisro@endava.com")
        cdk.Tags.of(self).add("project", "AI Functions investigation project")

        shared_env = self._provision_tables()
        layer = self._build_layer()
        bedrock = self._bedrock_policy()

        processor_fn = self._processor_lambda(shared_env, layer, bedrock)
        api_fn = self._api_lambda(shared_env, layer, bedrock)
        gw = self._rest_api(api_fn)
        dash_url = self._dashboard(gw.url)
        self._cw_subscriptions(processor_fn)
        test_fn = self._test_generator_lambda(processor_fn)

        CfnOutput(self, "ApiGatewayUrl", value=gw.url)
        CfnOutput(self, "DashboardSiteUrl", value=dash_url)
        CfnOutput(self, "ProcessorLambdaName", value=processor_fn.function_name)
        CfnOutput(self, "ApiLambdaName", value=api_fn.function_name)
        CfnOutput(self, "TestGeneratorLambdaName", value=test_fn.function_name)

    # ── DynamoDB ─────────────────────────────────────────────────────

    def _provision_tables(self) -> dict[str, str]:
        """Create logs + incidents DynamoDB tables. Returns env-var dict."""
        self._tbl_logs = ddb.Table(
            self, "AnalyzedLogsTable",
            table_name="log-analyzer-logs",
            partition_key=ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self._tbl_logs.add_global_secondary_index(
            index_name="gsi-level-time",
            partition_key=ddb.Attribute(name="log_level", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="created_at", type=ddb.AttributeType.STRING),
        )
        self._tbl_logs.add_global_secondary_index(
            index_name="gsi-category-time",
            partition_key=ddb.Attribute(name="category", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="created_at", type=ddb.AttributeType.STRING),
        )
        self._tbl_incidents = ddb.Table(
            self, "IncidentReportsTable",
            table_name="log-analyzer-incidents",
            partition_key=ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        return {
            "LOGS_TABLE": self._tbl_logs.table_name,
            "INCIDENTS_TABLE": self._tbl_incidents.table_name,
        }

    # ── Lambda helpers ───────────────────────────────────────────────

    def _bedrock_policy(self) -> iam.PolicyStatement:
        return iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["*"],
        )

    def _build_layer(self) -> lmb.LayerVersion:
        return lmb.LayerVersion(
            self, "AiFuncsDepsLayer",
            code=lmb.Code.from_asset(str(_ROOT / "lambda_layer")),
            compatible_runtimes=[lmb.Runtime.PYTHON_3_12],
            description="strands-ai-functions + pydantic for log analyzer lambdas",
        )

    def _processor_lambda(self, env: dict, layer: lmb.LayerVersion, policy: iam.PolicyStatement) -> lmb.Function:
        fn = lmb.Function(
            self, "CwProcessorFn",
            function_name="log-analyzer-cw-processor",
            runtime=lmb.Runtime.PYTHON_3_12,
            handler="cloudwatch_handler.handler",
            code=lmb.Code.from_asset(str(_ROOT / "lambda_code")),
            layers=[layer],
            timeout=Duration.minutes(5),
            memory_size=512,
            environment=env,
        )
        fn.add_to_role_policy(policy)
        self._tbl_logs.grant_read_write_data(fn)
        self._tbl_incidents.grant_read_write_data(fn)
        return fn

    # ── API Gateway ──────────────────────────────────────────────────

    def _rest_api(self, handler: lmb.Function) -> apigw.RestApi:
        gw = apigw.RestApi(
            self, "LogAnalyzerGateway",
            rest_api_name="log-analyzer",
            description="REST API for the AI log analyzer dashboard",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
        )
        proxy = apigw.LambdaIntegration(handler)
        api_node = gw.root.add_resource("api")
        _endpoints = {
            "logs": ["GET", "DELETE"],
            "stats": ["GET"],
            "correlate": ["POST"],
            "incidents": ["GET"],
            "analyze": ["POST"],
        }
        for name, verbs in _endpoints.items():
            child = api_node.add_resource(name)
            for verb in verbs:
                child.add_method(verb, proxy)
        return gw

    # ── S3 Dashboard ─────────────────────────────────────────────────

    def _dashboard(self, api_base_url: str) -> str:
        bkt = s3.Bucket(
            self, "DashboardSiteBucket",
            website_index_document="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        s3deploy.BucketDeployment(
            self, "UploadDashboardAssets",
            sources=[s3deploy.Source.asset(str(_ROOT / "dashboard"))],
            destination_bucket=bkt,
        )
        return bkt.bucket_website_url

    # ── CloudWatch Subscriptions ─────────────────────────────────────

    def _cw_subscriptions(self, target: lmb.Function) -> None:
        """Subscribe to log groups via CDK context:
            cdk deploy -c log_group_names='["/aws/lambda/my-fn"]'
        """
        raw_ctx = self.node.try_get_context("log_group_names")
        if not raw_ctx:
            return
        group_names = _json.loads(raw_ctx) if isinstance(raw_ctx, str) else raw_ctx
        for idx, lg_name in enumerate(group_names):
            lg_ref = cwlogs.LogGroup.from_log_group_name(self, f"WatchedLG{idx}", lg_name)
            cwlogs.SubscriptionFilter(
                self, f"LogSub{idx}",
                log_group=lg_ref,
                destination=cwdest.LambdaDestination(target),
                filter_pattern=cwlogs.FilterPattern.all_events(),
            )

    # ── Test log generator ──────────────────────────────────────────

    def _test_generator_lambda(self, processor: lmb.Function) -> lmb.Function:
        """Lambda that generates sample logs; its log group is auto-subscribed
        to the processor so logs flow through the AI pipeline automatically."""
        test_log_group = cwlogs.LogGroup(
            self, "TestGenLogGroup",
            log_group_name="/aws/lambda/log-analyzer-test-generator",
            removal_policy=RemovalPolicy.DESTROY,
            retention=cwlogs.RetentionDays.ONE_DAY,
        )
        fn = lmb.Function(
            self, "TestGeneratorFn",
            function_name="log-analyzer-test-generator",
            runtime=lmb.Runtime.PYTHON_3_12,
            handler="test_log_generator.handler",
            code=lmb.Code.from_asset(str(_ROOT / "lambda_code")),
            timeout=Duration.seconds(30),
            memory_size=128,
            log_group=test_log_group,
        )
        cwlogs.SubscriptionFilter(
            self, "TestGenSubscription",
            log_group=test_log_group,
            destination=cwdest.LambdaDestination(processor),
            filter_pattern=cwlogs.FilterPattern.all_events(),
        )
        return fn

    def _api_lambda(self, env: dict, layer: lmb.LayerVersion, policy: iam.PolicyStatement) -> lmb.Function:
        fn = lmb.Function(
            self, "RestApiFn",
            function_name="log-analyzer-api",
            runtime=lmb.Runtime.PYTHON_3_12,
            handler="api_handler.handler",
            code=lmb.Code.from_asset(str(_ROOT / "lambda_code")),
            layers=[layer],
            timeout=Duration.minutes(5),
            memory_size=512,
            environment=env,
        )
        fn.add_to_role_policy(policy)
        self._tbl_logs.grant_read_write_data(fn)
        self._tbl_incidents.grant_read_write_data(fn)
        return fn
