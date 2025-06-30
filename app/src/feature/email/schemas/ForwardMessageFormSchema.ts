/*
 * © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 *
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement
 * available at http://aws.amazon.com/agreement or other written agreement between
 * Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import {z} from "zod";

const forwardMessageFormSchema = z.object({
  email: z.string(),
  emails: z.array(z.string())
})
  .refine(input => {
    if(input.emails.length === 0) return true;
    return false;
  }, {
    message: "Enter at least one email address",
    path: ["emails"]
  })
  .refine(input => {
    const emailCheck = z.string().email();

    if(input.email.length > 0 && !emailCheck.safeParse(input.email).success) return false;
    return true;
  }, {
    message: "Enter a valid email address",
    path: ["email"]
  });

export {forwardMessageFormSchema};