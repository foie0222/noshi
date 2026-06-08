import { Stack, StackProps, RemovalPolicy, CfnOutput } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as fs from "fs";
import * as path from "path";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";

/**
 * FrontendStack — React ビルド成果物を S3 + CloudFront 配信（SPA フォールバック）。
 * frontend/dist を BucketDeployment で配信し、デプロイ時に CloudFront を無効化する。
 */
export class FrontendStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);
    const siteBucket = new s3.Bucket(this, "SiteBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY, // 静的・再生成可
      autoDeleteObjects: true,
    });
    const dist = new cloudfront.Distribution(this, "SiteDist", {
      defaultRootObject: "index.html",
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(siteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      errorResponses: [
        { httpStatus: 403, responseHttpStatus: 200, responsePagePath: "/index.html" },
        { httpStatus: 404, responseHttpStatus: 200, responsePagePath: "/index.html" },
      ],
    });

    // ビルド済み frontend/dist を配信（無ければ案内）。VITE_API_BASE は事前ビルドで注入済み。
    const distPath = path.resolve(__dirname, "../../../frontend/dist");
    if (fs.existsSync(distPath)) {
      new s3deploy.BucketDeployment(this, "DeploySite", {
        sources: [s3deploy.Source.asset(distPath)],
        destinationBucket: siteBucket,
        distribution: dist,
        distributionPaths: ["/*"], // デプロイ毎にキャッシュ無効化
      });
    }

    new CfnOutput(this, "SiteUrl", { value: `https://${dist.distributionDomainName}` });
    new CfnOutput(this, "SiteBucketName", { value: siteBucket.bucketName });
  }
}
