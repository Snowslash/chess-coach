import type { ComponentProps } from "react";

export function Label({ className = "", ...props }: ComponentProps<"label">) {
  return <label className={`field-label ${className}`.trim()} {...props} />;
}
