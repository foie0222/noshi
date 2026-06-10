import { Stack, StackProps, CfnOutput } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as route53 from "aws-cdk-lib/aws-route53";

interface CertificateStackProps extends StackProps {
  domainName: string;
  hostedZoneId: string;
  hostedZoneName: string;
}

/**
 * CertificateStack — CloudFront 用 ACM 証明書（**us-east-1 必須**）。
 * Route 53 ホストゾーンで DNS 検証する。別リージョンの FrontendStack からは
 * crossRegionReferences で参照する。ホストゾーンは手動作成のものを属性参照する。
 */
export class CertificateStack extends Stack {
  readonly certificate: acm.ICertificate;

  constructor(scope: Construct, id: string, props: CertificateStackProps) {
    super(scope, id, props);
    const zone = route53.HostedZone.fromHostedZoneAttributes(this, "Zone", {
      hostedZoneId: props.hostedZoneId,
      zoneName: props.hostedZoneName,
    });
    this.certificate = new acm.Certificate(this, "SiteCert", {
      domainName: props.domainName,
      validation: acm.CertificateValidation.fromDns(zone),
    });
    new CfnOutput(this, "CertificateArn", { value: this.certificate.certificateArn });
  }
}
