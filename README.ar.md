# ScaleLab — تطبيق ويب قابل للتوسع على AWS

هذا تنفيذ للمشروع الأول من أفكار التخرج لشهادة AWS Solutions Architect – Associate. التطبيق يعمل على EC2 داخل private subnets عبر منطقتي توافر، خلف Application Load Balancer وAuto Scaling، ويستخدم Amazon RDS for MySQL بنمط Multi-AZ. يقدم CloudFront الملفات الثابتة من S3 خاص، وتحمي AWS WAF نقطة الدخول.

## الملفات

- `README.md`: التوثيق الكامل وخطوات النشر والتحقق والتنظيف.
- `docs/architecture.drawio`: الرسم الأصلي القابل للتعديل في draw.io، بأيقونات AWS الرسمية.
- `docs/architecture.png`: صورة معاينة للرسم.
- `infra/template.yaml`: قالب CloudFormation للبنية كاملة.
- `app/`: التطبيق البسيط والملفات الثابتة.
- `scripts/`: أوامر نشر الملفات الثابتة والتحقق وحذف الـ stack.

## ملخص التصميم

- ALB في public subnets عبر منطقتي توافر، مع WAF وhealth check.
- EC2 Auto Scaling Group في private app subnets، بحد أدنى نسختين وتوسّع حسب متوسط CPU.
- NAT Gateway مستقل لكل منطقة توافر، وRDS في subnets معزولة دون إنترنت عام.
- بيانات الدخول ينشئها RDS ويحفظها في Secrets Manager، وتصل إليها EC2 بصلاحية IAM محدودة.
- CloudFront يقدم CSS من S3 باستخدام Origin Access Control، مع حظر الوصول العام إلى bucket.
- Session Manager لإدارة EC2 دون SSH أو bastion، وCloudWatch/SNS للمراقبة والتنبيهات.

## بدء سريع

راجع متطلبات الحساب والتكلفة أولًا، ثم من PowerShell:

```powershell
./scripts/deploy.ps1 -Region us-east-1
./scripts/verify.ps1 -Region us-east-1
./scripts/destroy.ps1 -Region us-east-1
```

كل التفاصيل، المتطلبات، نتائج التحقق، القيود، ومصادر AWS الرسمية موثقة في [README.md](README.md). القالب لم يُنشر على حساب AWS ضمن هذا التسليم؛ تشغيله ينشئ موارد مدفوعة.
