from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, X, Y, filedialog, messagebox, ttk
import tkinter as tk

try:
    from pypdf import PdfReader
except ImportError:  # Search stays optional; the calculator uses only the standard library.
    PdfReader = None


APP_DIR = Path(__file__).resolve().parent
REFERENCES_PATH = APP_DIR / "data" / "cost_references.json"


@dataclass(frozen=True)
class EstimateLine:
    label: str
    unit_cost_per_m2: float


def load_references() -> list[dict]:
    with REFERENCES_PATH.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def estimate(reference: dict, area_m2: float) -> dict:
    if area_m2 <= 0:
        raise ValueError("El área debe ser mayor que cero.")
    rate = float(reference["unit_cost_per_m2"])
    factor = area_m2 / float(reference.get("reference_area_m2") or area_m2)
    # If COSTO supplies an explicit benchmark area, scale its published line items
    # by the same factor. Otherwise only the published m² ratio is used.
    if reference.get("reference_area_m2"):
        total = float(reference["published_total"]) * factor
        lines = [
            {"label": row["label"], "amount": round(float(row["amount"]) * factor, 2)}
            for row in reference.get("breakdown", [])
        ]
    else:
        total = rate * area_m2
        lines = []
    return {
        "area_m2": area_m2,
        "unit_cost_per_m2": rate,
        "total": round(total, 2),
        "lines": lines,
    }


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def search_pdf_pages(paths: list[str], query: str, limit: int = 20) -> list[dict]:
    if PdfReader is None:
        raise RuntimeError("Falta pypdf. Instálalo con: python -m pip install pypdf")
    terms = [term for term in re.findall(r"[\wáéíóúñ]+", normalize(query)) if len(term) > 1]
    if not terms:
        raise ValueError("Escribe uno o más términos para buscar.")
    results = []
    for file_path in paths:
        path = Path(file_path)
        try:
            reader = PdfReader(str(path))
        except Exception as error:
            results.append({"error": f"No se pudo abrir {path.name}: {error}"})
            continue
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                raw = page.extract_text() or ""
            except Exception:
                continue
            searchable = normalize(raw)
            positions = [searchable.find(term) for term in terms]
            matched = [position for position in positions if position >= 0]
            score = sum(searchable.count(term) for term in terms)
            if score:
                flat = re.sub(r"\s+", " ", raw).strip()
                first_pos = min((searchable.find(term) for term in terms if term in searchable), default=0)
                start = max(0, first_pos - 180)
                excerpt = flat[start : start + 650]
                results.append({
                    "score": score,
                    "coverage": len(matched),
                    "span": max(matched) - min(matched) if len(matched) > 1 else 0,
                    "source": path.name,
                    "page": page_number,
                    "excerpt": excerpt,
                })
    results.sort(key=lambda item: (item.get("coverage", 0), -item.get("span", 0), item.get("score", 0)), reverse=True)
    return results[:limit]


class CosteoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.references = load_references()
        self.pdf_paths: list[str] = []
        self.title("Costeo Civil - MVP de referencias")
        self.geometry("1020x700")
        self.minsize(850, 560)
        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 17, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))

        header = ttk.Frame(self, padding=(20, 16, 20, 8))
        header.pack(fill=X)
        ttk.Label(header, text="Estimador civil basado en referencias", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Demo local: consulta de evidencia en PDFs y estimación preliminar por costo referencial/m².",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        tabs = ttk.Notebook(self)
        tabs.pack(fill=BOTH, expand=True, padx=16, pady=(4, 16))
        self.estimate_tab = ttk.Frame(tabs, padding=18)
        self.search_tab = ttk.Frame(tabs, padding=18)
        tabs.add(self.estimate_tab, text="Estimar")
        tabs.add(self.search_tab, text="Buscar en PDFs")
        self._build_estimate_tab()
        self._build_search_tab()

    def _build_estimate_tab(self) -> None:
        left = ttk.Frame(self.estimate_tab)
        left.pack(side=LEFT, fill=Y, padx=(0, 20))
        ttk.Label(left, text="Referencia COSTO", style="Section.TLabel").pack(anchor="w")
        self.reference_names = [row["name"] for row in self.references]
        self.reference_var = tk.StringVar(value=self.reference_names[0])
        self.reference_box = ttk.Combobox(
            left, textvariable=self.reference_var, values=self.reference_names, state="readonly", width=48
        )
        self.reference_box.pack(anchor="w", pady=(8, 14))
        self.reference_box.bind("<<ComboboxSelected>>", lambda _event: self._on_reference_changed())

        ttk.Label(left, text="Área del proyecto (m²)", style="Section.TLabel").pack(anchor="w")
        self.area_var = tk.StringVar(value="540")
        ttk.Entry(left, textvariable=self.area_var, width=18).pack(anchor="w", pady=(8, 14))
        self.area_var.trace_add("write", self._on_estimate_input_changed)
        ttk.Button(left, text="Calcular referencia", command=self._calculate).pack(anchor="w")
        ttk.Button(left, text="Exportar resultado a CSV", command=self._export_csv).pack(anchor="w", pady=(8, 0))

        self.reference_info = tk.Text(left, width=58, height=17, wrap="word", state="disabled")
        self.reference_info.pack(anchor="w", pady=(18, 0))

        right = ttk.Frame(self.estimate_tab)
        right.pack(side=LEFT, fill=BOTH, expand=True)
        ttk.Label(right, text="Resultado preliminar", style="Section.TLabel").pack(anchor="w")
        self.total_label = ttk.Label(right, text="S/ —", font=("Segoe UI", 24, "bold"))
        self.total_label.pack(anchor="w", pady=(12, 2))
        self.rate_label = ttk.Label(right, text="Costo referencial: —")
        self.rate_label.pack(anchor="w")
        self.coverage_label = ttk.Label(right, text="", wraplength=460)
        self.coverage_label.pack(anchor="w", pady=(10, 12))
        self.breakdown = ttk.Treeview(right, columns=("line", "amount"), show="headings", height=13)
        self.breakdown.heading("line", text="Grupo de partida publicado")
        self.breakdown.heading("amount", text="Monto escalado (S/)")
        self.breakdown.column("line", width=290)
        self.breakdown.column("amount", width=150, anchor="e")
        self.breakdown.pack(fill=BOTH, expand=True)
        ttk.Label(
            right,
            text="La proyección escala linealmente el costo de una referencia. No calcula metrados estructurales ni reemplaza una cotización profesional.",
            wraplength=460,
        ).pack(anchor="w", pady=(12, 0))
        self._show_reference_info()
        self._calculate()

    def _selected_reference(self) -> dict:
        return next(row for row in self.references if row["name"] == self.reference_var.get())

    def _show_reference_info(self) -> None:
        row = self._selected_reference()
        info = (
            f"Edición y vigencia: {row['issue']} · {row['validity']}\n"
            f"Ubicación: {row['location']}\n"
            f"Tipología: {row['description']}\n"
            f"Referencia publicada: S/ {row['unit_cost_per_m2']:,.2f}/m²\n"
            f"Fuente: {row['source']} · {row['pages']}\n\n"
            f"Alcance: {row['scope_note']}\n\n"
            "Esta muestra conserva la naturaleza y las limitaciones de la fuente. No incorpora ajustes por suelo, altura, transporte ni especificaciones diferentes."
        )
        self.reference_info.configure(state="normal")
        self.reference_info.delete("1.0", END)
        self.reference_info.insert("1.0", info)
        self.reference_info.configure(state="disabled")

    def _on_estimate_input_changed(self, *_args) -> None:
        self._calculate(show_errors=False)

    def _on_reference_changed(self) -> None:
        self._show_reference_info()
        self._calculate(show_errors=False)

    def _clear_estimate(self, message: str) -> None:
        self.last_estimate = None
        self.total_label.configure(text="S/ —")
        self.rate_label.configure(text="")
        self.coverage_label.configure(text=message)
        for item in self.breakdown.get_children():
            self.breakdown.delete(item)

    def _calculate(self, show_errors: bool = True) -> None:
        try:
            raw_area = self.area_var.get().strip()
            if not raw_area:
                raise ValueError("Ingresa un área mayor que cero.")
            area = float(raw_area.replace(",", "."))
            result = estimate(self._selected_reference(), area)
        except (ValueError, StopIteration) as error:
            self._clear_estimate("Escribe un área válida mayor que cero para actualizar el cálculo.")
            if show_errors:
                messagebox.showerror("Dato inválido", str(error))
            return
        self.last_estimate = result
        self.total_label.configure(text=f"S/ {result['total']:,.2f}")
        self.rate_label.configure(text=f"Costo referencial: S/ {result['unit_cost_per_m2']:,.2f}/m² × {area:,.2f} m²")
        reference = self._selected_reference()
        self.coverage_label.configure(
            text=f"Costo directo referencial · {reference['location']} · Vigencia {reference['validity']}. "
                 "No incluye gastos generales, utilidad, impuestos ni honorarios."
        )
        for item in self.breakdown.get_children():
            self.breakdown.delete(item)
        for line in result["lines"]:
            self.breakdown.insert("", END, values=(line["label"], f"S/ {line['amount']:,.2f}"))
        if not result["lines"]:
            self.breakdown.insert("", END, values=("La fuente no aporta un desglose cargado para esta referencia.", "—"))

    def _export_csv(self) -> None:
        if not hasattr(self, "last_estimate"):
            return
        target = filedialog.asksaveasfilename(
            title="Guardar estimación", defaultextension=".csv", filetypes=[("CSV", "*.csv")]
        )
        if not target:
            return
        reference = self._selected_reference()
        with open(target, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(["Referencia", reference["name"]])
            writer.writerow(["Fuente", reference["source"]])
            writer.writerow(["Vigencia", reference["validity"]])
            writer.writerow(["Ubicación", reference["location"]])
            writer.writerow(["Área m2", self.last_estimate["area_m2"]])
            writer.writerow(["Costo referencial S/m2", self.last_estimate["unit_cost_per_m2"]])
            writer.writerow(["Costo directo estimado S/", self.last_estimate["total"]])
            writer.writerow(["Alcance", reference["scope_note"]])
            if self.last_estimate["lines"]:
                writer.writerow([])
                writer.writerow(["Grupo de partida", "Monto escalado S/"])
                for line in self.last_estimate["lines"]:
                    writer.writerow([line["label"], line["amount"]])
        messagebox.showinfo("Exportación", f"Estimación guardada en:\n{target}")

    def _build_search_tab(self) -> None:
        controls = ttk.Frame(self.search_tab)
        controls.pack(fill=X)
        self.query_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.query_var).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(controls, text="Añadir PDFs", command=self._select_pdfs).pack(side=LEFT, padx=(8, 0))
        ttk.Button(controls, text="Buscar", command=self._search).pack(side=LEFT, padx=(8, 0))
        self.pdf_status = ttk.Label(self.search_tab, text="Aún no has añadido PDFs a la búsqueda.")
        self.pdf_status.pack(anchor="w", pady=(10, 8))
        self.results = tk.Text(self.search_tab, wrap="word")
        self.results.pack(fill=BOTH, expand=True)
        self.results.insert(
            "1.0",
            "Añade suplementos COSTO o expedientes técnicos descargados de SEACE. "
            "La búsqueda devuelve texto encontrado, documento y página para validar la evidencia original.\n\n"
            "El MVP no genera respuestas con un LLM ni convierte automáticamente tablas en precios aprobados.",
        )

    def _select_pdfs(self) -> None:
        selected = filedialog.askopenfilenames(title="Seleccionar PDFs", filetypes=[("PDF", "*.pdf")])
        for path in selected:
            if path not in self.pdf_paths:
                self.pdf_paths.append(path)
        self.pdf_status.configure(text=f"PDFs seleccionados: {len(self.pdf_paths)}")

    def _search(self) -> None:
        if not self.pdf_paths:
            messagebox.showwarning("Faltan PDFs", "Añade al menos un PDF para buscar.")
            return
        try:
            matches = search_pdf_pages(self.pdf_paths, self.query_var.get())
        except (ValueError, RuntimeError) as error:
            messagebox.showerror("Búsqueda", str(error))
            return
        self.results.delete("1.0", END)
        if not matches:
            self.results.insert("1.0", "No se encontró coincidencia. Revisa términos, calidad del texto extraído o si el PDF necesita OCR.")
            return
        for match in matches:
            if "error" in match:
                self.results.insert(END, match["error"] + "\n\n")
                continue
            self.results.insert(END, f"{match['source']} · página {match['page']} · coincidencias {match['score']}\n")
            self.results.insert(END, match["excerpt"] + "\n\n" + ("─" * 70) + "\n\n")


def smoke_check() -> None:
    refs = load_references()
    sports = next(ref for ref in refs if ref["id"] == "sport-court-aug-2026")
    result = estimate(sports, 540)
    smaller_result = estimate(sports, 270)
    assert abs(result["total"] - 119269.64) < 0.01, result
    assert abs(sum(row["amount"] for row in result["lines"]) - result["total"]) < 0.03, result
    assert abs(smaller_result["total"] - result["total"] / 2) < 0.01, smaller_result
    print(f"OK: {len(refs)} referencias cargadas; losa 540 m² = S/ {result['total']:,.2f}; 270 m² = S/ {smaller_result['total']:,.2f}; desglose cuadra.")
    try:
        import tkinter
        print(f"OK: interfaz Tk disponible (Tcl/Tk {tkinter.TkVersion}).")
    except Exception as error:
        raise SystemExit(f"Tkinter no disponible: {error}")
    if PdfReader is None:
        print("Aviso: búsqueda PDF requiere instalar pypdf.")
    else:
        print(f"OK: búsqueda PDF disponible (pypdf {PdfReader.__module__.split('.')[0]}).")


if __name__ == "__main__":
    if "--smoke-check" in sys.argv:
        smoke_check()
    else:
        CosteoApp().mainloop()
