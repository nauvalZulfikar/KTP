import { ProductsPanel } from "@/components/panels/products-panel";

export default function ProductsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Product List Change</h1>
      <ProductsPanel />
    </div>
  );
}
