import axios from "axios";
import { useMutation } from "@tanstack/react-query";

type ForwardMessageData = {
  case_id: string;
  emails: string[];
}

const forwardMessage = async(emailData: ForwardMessageData): Promise<string> => {
  const { data } = await axios.post(`/messages/${emailData.case_id}/forward`, emailData);
  return data;
}

export const useForwardMessage = () => {
  return useMutation<string, Error, ForwardMessageData>({
    mutationFn: forwardMessage,
    onSuccess: () => {
      //
    },
    onError: (error: any) => {
      console.error("Error forward email:", error);
    }
  });
};