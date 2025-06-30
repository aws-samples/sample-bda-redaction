import axios from "axios";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { Rule } from "../../../foundation/rules/types";

type ToggleRuleParams = {
  rule_id: string;
  enabled: boolean
};

const toggleRule = async(toggleRulesData: ToggleRuleParams): Promise<Rule> => {
  const { data } = await axios.patch(`/rules/${toggleRulesData.rule_id}`, toggleRulesData);
  return data;
}

/**
 * Hook for toggling the enabled status of a rule
 */
export const useToggleRule = () => {
  const queryClient = useQueryClient();

  return useMutation<Rule, Error, ToggleRuleParams>({
    mutationFn: toggleRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["Rules"] });
    },
    onError: (error: any) => {
      console.error("Error changing enabled status of rule:", error);
    },
    gcTime: 0
  });
};