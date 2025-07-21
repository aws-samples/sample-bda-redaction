/*
 * © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 *
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement
 * available at http://aws.amazon.com/agreement or other written agreement between
 * Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import { useOutletContext } from "react-router-dom";
import { AppHelperContextType } from "../types";

/**
 * Exposes items passed to React Router Outlet context to component as a hook
 * @see https://reactrouter.com/en/main/hooks/use-outlet-context
 * @returns AppHelperContextType
 */
function useAppHelpers(): AppHelperContextType {
    return useOutletContext<AppHelperContextType>();
}

export {
  useAppHelpers
};