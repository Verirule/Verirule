alter table public.audit_exports
  drop constraint if exists audit_exports_format_check;

alter table public.audit_exports
  add constraint audit_exports_format_check
  check (format in ('pdf','csv','zip'));
