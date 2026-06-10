import { Stack, StackProps, RemovalPolicy, CfnOutput } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as fs from "fs";
import * as path from "path";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3deploy from "aws-cdk-lib/aws-s3-deployment";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as targets from "aws-cdk-lib/aws-route53-targets";

interface FrontendStackProps extends StackProps {
  // 独自ドメイン（#72）。未指定なら CloudFront 既定ドメインのみで配信する。
  domainName?: string;
  hostedZoneId?: string;
  hostedZoneName?: string;
  certificate?: acm.ICertificate; // CloudFront 用 ACM（us-east-1、CertificateStack から参照）
}

/**
 * FrontendStack — React ビルド成果物を S3 + CloudFront 配信（SPA フォールバック）。
 * frontend/dist を BucketDeployment で配信し、デプロイ時に CloudFront を無効化する。
 * 独自ドメインが渡された場合は CloudFront に代替ドメイン名＋証明書を付け、
 * Route 53 に Alias（A/AAAA）を張る（#72）。
 */
export class FrontendStack extends Stack {
  constructor(scope: Construct, id: string, props?: FrontendStackProps) {
    super(scope, id, props);
    const domainName = props?.domainName;
    const useDomain = !!(
      domainName &&
      props?.certificate &&
      props?.hostedZoneId &&
      props?.hostedZoneName
    );
    const siteBucket = new s3.Bucket(this, "SiteBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY, // 静的・再生成可
      autoDeleteObjects: true,
    });
    // 旧 CloudFront ドメイン等、独自ドメイン以外でのアクセスは noshi.me へ 301 する（#72）。
    // viewer-request で Host を見て分岐。パス・クエリは保持する。
    const redirectFn = useDomain
      ? new cloudfront.Function(this, "ApexRedirect", {
          comment: `redirect non-${domainName} hosts to ${domainName}`,
          code: cloudfront.FunctionCode.fromInline(
            [
              "function handler(event) {",
              "  var req = event.request;",
              "  var host = req.headers.host && req.headers.host.value;",
              `  if (host && host !== '${domainName}') {`,
              "    var qs = req.querystring || {};",
              "    var q = Object.keys(qs).map(function (k) { return k + '=' + qs[k].value; }).join('&');",
              `    var loc = 'https://${domainName}' + req.uri + (q ? '?' + q : '');`,
              "    return { statusCode: 301, statusDescription: 'Moved Permanently', headers: { location: { value: loc } } };",
              "  }",
              "  return req;",
              "}",
            ].join("\n"),
          ),
        })
      : undefined;

    const dist = new cloudfront.Distribution(this, "SiteDist", {
      defaultRootObject: "index.html",
      ...(useDomain ? { domainNames: [domainName as string], certificate: props?.certificate } : {}),
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(siteBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        ...(redirectFn
          ? {
              functionAssociations: [
                {
                  function: redirectFn,
                  eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
                },
              ],
            }
          : {}),
      },
      errorResponses: [
        { httpStatus: 403, responseHttpStatus: 200, responsePagePath: "/index.html" },
        { httpStatus: 404, responseHttpStatus: 200, responsePagePath: "/index.html" },
      ],
    });

    // 独自ドメイン: Route 53 に Alias（apex は CNAME 不可なので A/AAAA Alias）を張る（#72）。
    if (useDomain) {
      const zone = route53.HostedZone.fromHostedZoneAttributes(this, "Zone", {
        hostedZoneId: props?.hostedZoneId as string,
        zoneName: props?.hostedZoneName as string,
      });
      const aliasTarget = route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(dist));
      new route53.ARecord(this, "AliasA", {
        zone,
        recordName: domainName,
        target: aliasTarget,
      });
      new route53.AaaaRecord(this, "AliasAAAA", {
        zone,
        recordName: domainName,
        target: aliasTarget,
      });
    }

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

    new CfnOutput(this, "SiteUrl", {
      value: useDomain ? `https://${domainName}` : `https://${dist.distributionDomainName}`,
    });
    new CfnOutput(this, "CloudFrontUrl", { value: `https://${dist.distributionDomainName}` });
    new CfnOutput(this, "SiteBucketName", { value: siteBucket.bucketName });
  }
}
