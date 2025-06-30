import axios from "axios";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { CreateRuleFormData } from "../../../foundation/rules/types";

const createRule = async(ruleData: CreateRuleFormData): Promise<CreateRuleFormData> => {
  const rules = ruleData.ruleLineItems.filter(rule => {
    return rule.fieldName !== "" && rule.fieldValue !== "";
  });

  if(ruleData.dateRange && ruleData.dateRange.startDate) {
    rules.push({
      fieldName: "date_sent",
      fieldCondition: "between",
      fieldValue: `${ruleData.dateRange.startDate}-${ruleData.dateRange.endDate}`
    });
  }

  const payload = {
    description: ruleData.description,
    folderId: ruleData.folderId,
    criteria: rules,
  };

  const { data } = await axios.post("/rules", payload);
  return data;
}

export const useCreateRule = () => {
  const queryClient = useQueryClient();

  return useMutation<CreateRuleFormData, Error, CreateRuleFormData>({
    mutationFn: createRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["Rules"] });
    },
    onError: (error: any) => {
      console.error("Error creating rule:", error);
    }
  });
};