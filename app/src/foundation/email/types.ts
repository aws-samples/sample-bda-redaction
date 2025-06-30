/*
  CaseID: Unique case id for each email received
  RawFilePath: Name of the raw email file along with the prefixes if any
  RawBucketName: Name of the S3 bucket where raw email files are stored
  EmailSubject: Subject of the email received (redacted)
  EmailBody: First 100 characters of the body (redacted)
  EmailReceiveTime: Date and time email is received
  FromAddress: Email address of the sender
  DominantLanguage: Dominant language of the body
  ProcessedBucketName: Name of the S3 bucket where processed emails will be saved
  ProcessedFilePath: Name of the process email file along with prefixes if any
  FolderID: Unique ID of the folder in the UI (default will be “general_inbox”)
  BodyProcessedTime: Date and and time when body redaction processing completed
  BodyStatus: Date and and time when body redaction processing completed
  AttachmentProcessedTime: Date and and time when attachment redaction processing completed
  AttachmentStatus: Status of attachment processing (Open/Failed/Processed)
*/

export type Email = {
  CaseID: string;
  RawFilePath: string;
  RawBucketName: string;
  EmailSubject: string;
  EmailBody: string;
  EmailReceiveTime: string;
  FromAddress: string;
  DominantLanguage: string;
  ProcessedBucketName: string;
  ProcessedFilePath: string;
  FolderID: string;
  BodyProcessedTime: string;
  BodyStatus: string;
  AttachmentProcessedTime: string;
  AttachmentStatus: string;
  RedactedBody: string;
  folder?: {
    FolderID: string;
    Name: string;
  };
  files?: {
    name: string;
    url: string;
  }[];
};