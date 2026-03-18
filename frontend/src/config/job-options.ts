/**
 * Application Status and Rejection Reason options (match backend / Google Sheet).
 * Used for dropdowns on New Job and Job Detail pages.
 */

export const APPLICATION_STATUS_OPTIONS = [
  "Have Not Applied",
  "Submitted - Pending Response",
  "Rejected",
  "Interviewing",
  "Offer Extended - In Progress",
  "Sent Follow Up Email",
  "Re-Applied With Updated Resume",
  "N/A",
] as const;

export const REJECTION_REASON_OPTIONS = [
  "N/A",
  "Auto-Reject: No Feedback Provided",
  "1st Round Rejection - Feedback Provided",
  "1st Round Rejection - No Feedback Provided",
  "Middle Round Rejection - Feedback Provided",
  "Middle Round Rejection - No Feedback Provided",
  "Final Round Rejection - Feedback Provided",
  "Final Round Rejection - No Feedback Provided",
  'Generic "Not A Good Fit"',
  "Filled - Internal",
  "Eliminated Role",
  "Changed Job Scope",
  "No New Applicants",
  "Applied Too Late",
  "No Response: Sent Email",
  "Post-Interview Follow-Up Email",
  "Ghosted",
  "Job Rec Removed/Deactivated",
  "Offer Extended - Did Not Accept",
  "Rescinded Application (Self) / Decided not a good fit",
  "Not For Me",
] as const;

export const DEFAULT_APPLICATION_STATUS = "Have Not Applied";

export const SOURCE_PLATFORM_OPTIONS = [
  "",
  "LinkedIn",
  "Indeed",
  "Company Site",
  "Referral",
  "Recruiter",
  "Other",
] as const;

export const WORK_ARRANGEMENT_OPTIONS = ["", "Remote", "Hybrid", "Onsite"] as const;
