#!/usr/bin/env python3
"""CDK app entry point for Log Analyzer infrastructure."""

import aws_cdk as cdk

from stack import LogAnalyzerStack

app = cdk.App()

LogAnalyzerStack(
    app,
    "LogAnalyzerStack",
    description="AI-powered log analyzer: CloudWatch → Lambda → DynamoDB → Dashboard",
)

app.synth()
