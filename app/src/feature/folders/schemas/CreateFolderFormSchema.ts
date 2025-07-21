/*
 * © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 *
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement
 * available at http://aws.amazon.com/agreement or other written agreement between
 * Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import {z} from "zod";

const createFolderFormSchema = z.object({
    name: z.string().min(3, "This field is required and has to have a minimum of 3 characters"),
    description: z.string().optional(),
});

export {createFolderFormSchema};