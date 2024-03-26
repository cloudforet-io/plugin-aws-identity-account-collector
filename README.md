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

* The Control Tower serves as a central location for managing multiple AWS accounts. It provides a set of pre-configured
  blueprints that help you quickly set up a multi-account environment based on AWS best practices.
* The Control Tower uses AWS Organizations to create and manage accounts. This is the main reason why it is important to
  understand how AWS Organizations work(explained below).
* Overall, there are some main components in Control Tower that are important to understand:
    * **Landing Zone**: The landing zone is the environment that you set up using Control Tower. It is the environment
      that you use to manage multiple AWS accounts.
    * **Organizational Units (OUs)**: OUs are used to group accounts together. They are used to apply policies to a
      group of accounts.
    * **Security**: Security is a key OU of Control Tower. It is used to ensure that accounts in the organization
      are secure. There are 2 main components in the Security OU:
        * **Audit**: The audit account is used to store logs and audit information for the organization.
        * **Log Archive**: The log archive account is used to store logs and audit information for the organization.
    * **Service Control Policies (SCPs)**: SCPs are used to control permissions in the organization. They are used to
      restrict permissions for accounts in the organization.
    * **Guardrails**: Guardrails are used to enforce policies in the organization. They are used to ensure that accounts
      in the organization are compliant with the policies.

## Organization Overview

<img width="443" alt="스크린샷 2024-03-12 오후 9 44 52" src="https://github.com/Sooyoung98/plugin-aws-identity-account-collector/assets/79274380/5dd430cc-666a-4e9f-b1fc-9bea950157cf">

* AWS Organzations is a service that allows you to create and manage multiple AWS accounts. It is used to group accounts
  together and apply policies to them.
* Overall, there are some main components in Organizations that are important to understand:
    * **Master Account(=Management Account in Control Tower)**: The primary AWS account that is used to create and
      manage an AWS Organization. The account is responsible for creating member accounts, defining organizational
      units (OUs), applying service control policies (SCPs), and managing billing and payment methods for all accounts
      within the organization.
    * **Organizational Units (OUs)**: An organizational unit is a logical grouping of AWS accounts within an AWS
      Organization. OUs help in organizing and managing accounts based on common business needs.
    * **Service Control Policies (SCPs)**: SCPs are policy documents that allow you to control which AWS services and
      features can be accessed by the accounts within an AWS Organization, or within specific OUs or individual
      accounts.

## Code Flow

![sync_aws_account_flow](https://github.com/Sooyoung98/plugin-aws-identity-account-collector/assets/79274380/bd4abed5-88de-4223-a0fd-7a2fabc2f73f)

