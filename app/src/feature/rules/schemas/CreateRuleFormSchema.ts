/*
 * © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 *
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement
 * available at http://aws.amazon.com/agreement or other written agreement between
 * Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import {z} from "zod";

const createRuleFormSchema = z.object({
  description: z.string().min(3, "This field is required"),
  folderId: z.string().min(1, "This field is required"),
  ruleLineItems: z.array(
    z.object({
      fieldName: z.string().optional(),
      fieldCondition: z.string().optional(),
      fieldValue: z.string().optional(),
    })
  ),
  dateRange: z.object({
    startDate: z.string().optional(),
    endDate: z.string().optional()
  })
})
  .refine(inputs => {
    if(inputs.ruleLineItems.length === 1 && inputs.ruleLineItems[0].fieldName === "" && (!inputs.dateRange.startDate && !inputs.dateRange.endDate)) return false;
    return true;
  }, {
    message: "You must specify either a date range or at least 1 filtering condition",
    path: ["conditions"]
  });

export {createRuleFormSchema};