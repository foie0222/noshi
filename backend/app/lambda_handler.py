"""AWS Lambda エントリポイント（API Gateway → FastAPI）。

CDK ApiStack の handler は app.lambda_handler.handler を指す。
本番デプロイ時は fastapi/mangum/boto3 を Lambda Layer か bundling で同梱する。
"""
from mangum import Mangum

from app.main import app

handler = Mangum(app)
