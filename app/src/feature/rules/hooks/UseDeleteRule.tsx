import axios from "axios";
import { useQueryClient, useMutation } from "@tanstack/react-query";

const deleteRule = async(rule_id: string): Promise<string> => {
  const { data } = await axios.delete(`/rules/${rule_id}`);
  return data;
}

export const useDeleteRule = () => {
  const queryClient = useQueryClient();

  return useMutation<string, Error, string>({
    mutationFn: deleteRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["Rules"] });
    },
    onError: (error: any) => {
      console.error("Error deleting rule:", error);
    }
  });
};