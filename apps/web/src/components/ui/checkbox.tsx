import type { ComponentProps } from "react";

export function Checkbox({ className = "", ...props }: ComponentProps<"input">) {
  return <input className={`field-checkbox ${className}`.trim()} type="checkbox" {...props} />;
}
