# plugin-aws-identity-account-collector

* This collector collects aws accounts included within AWS Control Tower.
* Specifically, this collector provides details needed for SpaceONE to automatically create General Service Accounts for
  customers.
* Try looking into these documentations for better understanding of how Control Tower works and how it is structured.
    * [AWS Control Tower Overview](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)
    * [AWS Control Tower Documentation](https://docs.aws.amazon.com/controltower/latest/userguide/welcome.html)
    * [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html)
## Control Tower Overview
<img width="574" alt="스크린샷 2024-03-12 오후 9 42 25" src="https://github.com/Sooyoung98/plugin-aws-identity-account-collector/assets/79274380/b5407ffb-e2a8-4488-8c9c-d823cbe1cf3a">

## Organization Overview
<img width="443" alt="스크린샷 2024-03-12 오후 9 44 52" src="https://github.com/Sooyoung98/plugin-aws-identity-account-collector/assets/79274380/5dd430cc-666a-4e9f-b1fc-9bea950157cf">


## Code Flow
![sync_aws_account_flow](https://github.com/Sooyoung98/plugin-aws-identity-account-collector/assets/79274380/bd4abed5-88de-4223-a0fd-7a2fabc2f73f)

