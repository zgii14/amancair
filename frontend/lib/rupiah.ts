export function rupiah(n: number): string {
  return "Rp" + new Intl.NumberFormat("id-ID").format(n);
}
