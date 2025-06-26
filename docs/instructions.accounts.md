DropboxAccount (Dropbox Account Folder Information)
  dropbox_account_folder_name
  application_files: list[DropboxAccountApplicationFile]
  client_list_info:  list[DropboxAccountClientListInfo] 
  best_info: DropboxAccountBestInfo
  salesforce_account_information: Salesforce Account Information [list]
  

DropboxAccountClientList 
  Account Name
  First Name
  Middle Name
  Last Name
  Birthdate
  Gender
  Phone
  Address
  Email

DropboxAccountFromApplicationFiles
  total_account_application_files
  processed_account_application_files
  failed_account_application_files
  dropbox_accounts_application_files: list[DopboxAccountApplicationFile]


DropboxAccountApplicationFile
   owner: DropboxAccountApplicationInfo
   joint_owner: DropboxAccountApplicationInfo
   dropbox_account: DropboxAccount


Salesforce Account Information
  num_accounts -1 (default, means no salesforce account information was stored)
  Names found [list of Salesforce Account Names]
  Household [Salesforce Account]
  Head [SalesforceAccount]
  Members [SalesforceAccount]

  SalesforceAccount
    account_name
    type [Contact]
    role [Household Head, Member]
    stage
    email
    phone
    mail_address
    ssn/tax_id
    relationships [list of Salesforce Account]





The analysis should be about what data that is not in Salesforce, but is in Dropbox that needs to be input in Salesforce.

We also want to have a consistent mapping from what we have in Dropbox to Salesforce relationships.

Typically an account in Salesforce has a Household, and a Household head.  If it's a joint account then the Joint Account maps to a Household member.

In the case of 'Montesino, Maria', the Dropbox account should be 
mapped to a Household Head with name "Maria Montesino Household",
and a Household head with name "Maria Montesino".

In dropbox there is really one Dropbox account folder, which contains all the applications and records for the account, even 
if it's a joint account.  
The Dropbox account folder name typically has information about the last name, first name and and even some information about the joint account member.  Sometimes it also has information about the son(s) or (daughter(s)) of the account holder.

For example, a Dropbox folder name 'Rubro, John & Leah', indicates potentially a joint account.  
We want to take a look at the Dropbox Account from Application Files to see if we can find any information about Rubro. 
If we find that the Account Holder is John Rubro this will 
map to Salesforce Account John Rubro (Head).
If we find a Joint Account, and the name is Leah Smith, this
will map to Salesforce Account Leah Smith.
These two accounts should be linked to a Salesforce Account (Household): Rubro Household.
Salesforce Account: Rubro Household
Salesforce Account (Head): John Rubro
Salesforce Account (Member): Leah Smith

Now, we want to also see the information from the Dropbox Account from Client List File and compare it with what is 
in Salesforce. The Dropbox Account from Client List File always
maps to the Salesforce Account Household and Salesforce Account Head.
We want to map the corresponding following fields which may have some name and structure differences, but in the end these are the basic fields:
Account name
First name
Middle Name
Last name
Birthdate
Gender
Address
Phone
Email

In the analysis report I would like to see clear comparison of
how Dropbox Account Information maps to Salesforce Account Information.





