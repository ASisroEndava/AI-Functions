#!/usr/bin/env python3
import aws_cdk as cdk
from stack import LogAnalyzerStack

app = cdk.App()
LogAnalyzerStack(app, "LogAnalyzerStack")
app.synth()
