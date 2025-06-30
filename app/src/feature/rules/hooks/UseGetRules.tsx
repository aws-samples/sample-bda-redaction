import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import { Rule } from "../../../foundation/rules/types";

const getRules = async(): Promise<Rule[]> => {
  const { data } = await axios.get("/rules");
  return data;
}

export const useGetRules = () => {
  return useQuery<Rule[], Error>({
    queryKey: ['Rules'],
    queryFn: getRules,
    retry: false
  });
};