# Code Generation — Plan（intent-009 / CDK）
- [x] infra/cdk/lib/data-stack.ts（DynamoDB/S3/KMS, PITR/TTL/GSI, RETAIN）
- [x] infra/cdk/lib/messaging-stack.ts（SQS+DLQ）
- [x] infra/cdk/lib/api-stack.ts（API GW + Lambda + 最小権限）
- [x] infra/cdk/lib/worker-stack.ts（抽出ワーカー Lambda + SQS source）
- [x] infra/cdk/lib/frontend-stack.ts（S3 + CloudFront SPA）
- [x] infra/cdk/bin/noshi.ts, cdk.json, tsconfig, package.json
- [x] 検証: tsc / cdk synth（CloudFormation 生成）
