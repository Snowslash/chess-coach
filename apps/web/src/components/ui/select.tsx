import type { ComponentProps } from "react";

export function Select({ className = "", ...props }: ComponentProps<"select">) {
  return <select className={`field-input ${className}`.trim()} {...props} />;
}
