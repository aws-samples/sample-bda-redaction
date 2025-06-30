import axios from "axios";
import { useMutation } from "@tanstack/react-query";

type ExportMessageData = {
  case_id: string[];
}

const exportMessage = async(messageData: ExportMessageData): Promise<any> => {
  const { data } = await axios.post(`/messages/export`, messageData, {
    headers: {
      "Accept": "text/csv"
    }
  });
  return data;
}

export const useExportMessage = () => {
  return useMutation<any, Error, ExportMessageData>({
    mutationFn: exportMessage,
    onSuccess: async (messages) => {
      const downloadUrl = window.URL.createObjectURL(new Blob([atob(messages.body)]));
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', 'exported_messages.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
    onError: (error: any) => {
      console.error("Error exporting messages:", error);
    }
  });
};