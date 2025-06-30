import { SelectProps } from "@cloudscape-design/components";

function getSelectOption(
  value?: string | SelectProps.Option,
  collection?: SelectProps.Option[]
): SelectProps.Option | null {
  const item = collection?.filter((item) => {
    if(typeof value === "string") return item.value === value;
    else return item.value === value?.value
  });

  if (item?.length) return item[0];

  return null;
}

export {
  getSelectOption
}