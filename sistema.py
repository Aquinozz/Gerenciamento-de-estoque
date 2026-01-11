import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from datetime import datetime
import os
import tempfile

class SistemaSupermercado:
    def __init__(self, root):
        self.root = root
        self.root.title("SGE Pro - Gestão Comercial Completa")
        self.root.geometry("1200x850")
        
        self.banco = "sistema.db"
        self.configurar_banco()
        
        self.carrinho_dados = [] 
        self.total_venda = 0.0
        
        self.criar_interface()
        self.vincular_atalhos()
        self.ent_codigo_pdv.focus_set()

    def conectar(self):
        return sqlite3.connect(self.banco, timeout=10)

    def configurar_banco(self):
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS estoque (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_barras TEXT UNIQUE,
                    nome TEXT NOT NULL,
                    quantidade INTEGER NOT NULL,
                    preco_venda REAL NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT,
                    total REAL,
                    recebido REAL,
                    troco REAL,
                    metodo TEXT,
                    itens_texto TEXT
                )
            """)
            conn.commit()

    def vincular_atalhos(self):
        self.root.bind("<F5>", lambda e: self.abrir_tela_pagamento())
        self.root.bind("<F1>", lambda e: self.ent_codigo_pdv.focus_set())
        self.root.bind("<Delete>", lambda e: self.remover_item())

    def criar_interface(self):
        self.abas = ttk.Notebook(self.root)
        self.aba_pdv = ttk.Frame(self.abas)
        self.aba_estoque = ttk.Frame(self.abas)
        self.aba_historico = ttk.Frame(self.abas)
        
        self.abas.add(self.aba_pdv, text=" [F1] CAIXA ")
        self.abas.add(self.aba_estoque, text=" ESTOQUE ")
        self.abas.add(self.aba_historico, text=" HISTÓRICO E RELATÓRIOS ")
        self.abas.pack(expand=1, fill="both")
        
        self.setup_pdv()
        self.setup_estoque()
        self.setup_historico()

    def setup_pdv(self):
        frame_esq = tk.Frame(self.aba_pdv, padx=10, pady=10)
        frame_esq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(frame_esq, text="QUANTIDADE * CÓDIGO (Ex: 3*123):", font=("Arial", 10, "bold")).pack(anchor="w")
        self.ent_codigo_pdv = tk.Entry(frame_esq, font=("Arial", 22), bg="#e8f5e9")
        self.ent_codigo_pdv.pack(fill=tk.X, pady=5)
        self.ent_codigo_pdv.bind("<Return>", lambda e: self.processar_leitura())

        cols = ("Cod", "Nome", "Qtd", "Unit", "Sub")
        self.tree_carrinho = ttk.Treeview(frame_esq, columns=cols, show="headings")
        for col in cols: self.tree_carrinho.heading(col, text=col)
        self.tree_carrinho.pack(fill=tk.BOTH, expand=True)

        tk.Button(frame_esq, text="Remover Item [DEL]", bg="#ef5350", fg="white", command=self.remover_item).pack(anchor="w", pady=5)

        frame_dir = tk.Frame(self.aba_pdv, width=300, bg="#f5f5f5", padx=20)
        frame_dir.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(frame_dir, text="TOTAL", font=("Arial", 18, "bold"), bg="#f5f5f5").pack(pady=30)
        self.lbl_total = tk.Label(frame_dir, text="R$ 0.00", font=("Arial", 35, "bold"), fg="#2e7d32", bg="#f5f5f5")
        self.lbl_total.pack()

        tk.Button(frame_dir, text="PAGAMENTO (F5)", font=("Arial", 14, "bold"), 
                  bg="#2e7d32", fg="white", height=3, command=self.abrir_tela_pagamento).pack(fill=tk.X, side=tk.BOTTOM, pady=20)

    def processar_leitura(self):
        entrada = self.ent_codigo_pdv.get().strip()
        self.ent_codigo_pdv.delete(0, tk.END)
        if not entrada: return
        
        qtd, cod = 1, entrada
        if "*" in entrada:
            try:
                qtd_str, cod = entrada.split("*")
                qtd = int(qtd_str)
            except: pass

        with self.conectar() as conn:
            res = conn.execute("SELECT nome, preco_venda, quantidade FROM estoque WHERE codigo_barras = ?", (cod,)).fetchone()

        if res:
            nome, preco, est = res
            if est >= qtd:
                sub = preco * qtd
                self.carrinho_dados.append({'cod': cod, 'nome': nome, 'qtd': qtd, 'unit': preco, 'sub': sub})
                self.tree_carrinho.insert("", 0, values=(cod, nome, qtd, f"R$ {preco:.2f}", f"R$ {sub:.2f}"))
                self.total_venda += sub
                self.lbl_total.config(text=f"R$ {self.total_venda:.2f}")
            else: messagebox.showwarning("Aviso", f"Estoque insuficiente! Apenas {est} disponíveis.")
        else: messagebox.showerror("Erro", "Produto não encontrado.")

    def abrir_tela_pagamento(self):
        if not self.carrinho_dados: return
        self.win_pag = tk.Toplevel(self.root)
        self.win_pag.title("Finalizar Venda")
        self.win_pag.geometry("400x450")
        self.win_pag.grab_set()

        tk.Label(self.win_pag, text=f"TOTAL: R$ {self.total_venda:.2f}", font=("Arial", 20, "bold")).pack(pady=20)
        
        self.combo_metodo = ttk.Combobox(self.win_pag, values=["Dinheiro", "Cartao", "Pix"], state="readonly")
        self.combo_metodo.current(0)
        self.combo_metodo.pack(pady=5)

        tk.Label(self.win_pag, text="Valor Recebido:").pack()
        self.ent_recebido = tk.Entry(self.win_pag, font=("Arial", 16))
        self.ent_recebido.pack(pady=5)
        self.ent_recebido.focus_set()
        
        self.ent_recebido.bind("<KeyRelease>", self.calc_troco_venda)
        self.ent_recebido.bind("<Return>", lambda e: self.finalizar_venda_db())

        self.lbl_troco_win = tk.Label(self.win_pag, text="Troco: R$ 0.00", font=("Arial", 14, "bold"), fg="blue")
        self.lbl_troco_win.pack(pady=20)

        tk.Button(self.win_pag, text="CONFIRMAR (ENTER)", bg="green", fg="white", font=("Arial", 12, "bold"), 
                  height=2, command=self.finalizar_venda_db).pack(fill=tk.X, padx=30)

    def gerar_layout_cupom(self, data, recebido, troco, metodo):
        cupom =  "      SUPERMERCADO SGE PRO      \n"
        cupom += "--------------------------------\n"
        cupom += f"DATA: {data}\n"
        cupom += "--------------------------------\n"
        cupom += "ITEM         QTD   UNIT    TOTAL\n"
        for item in self.carrinho_dados:
            nome = item['nome'][:12].ljust(12)
            cupom += f"{nome} {str(item['qtd']).rjust(3)} {str(item['unit']).rjust(6)} {str(item['sub']).rjust(8)}\n"
        cupom += "--------------------------------\n"
        cupom += f"TOTAL:            R$ {self.total_venda:>10.2f}\n"
        cupom += f"RECEBIDO:         R$ {recebido:>10.2f}\n"
        cupom += f"TROCO:            R$ {troco:>10.2f}\n"
        cupom += f"PAGAMENTO:        {metodo.upper()}\n"
        cupom += "--------------------------------\n"
        cupom += "   OBRIGADO E VOLTE SEMPRE!   \n"
        return cupom

    def finalizar_venda_db(self):
        try:
            recebido_str = self.ent_recebido.get().replace(',', '.')
            recebido = float(recebido_str) if recebido_str else 0.0
            if recebido < self.total_venda:
                messagebox.showerror("Erro", "Valor insuficiente!")
                return

            metodo = self.combo_metodo.get()
            data_venda = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            troco = recebido - self.total_venda
            texto_cupom = self.gerar_layout_cupom(data_venda, recebido, troco, metodo)

            with self.conectar() as conn:
                cursor = conn.cursor()
                for item in self.carrinho_dados:
                    cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE codigo_barras = ?", 
                                 (item['qtd'], item['cod']))
                cursor.execute("INSERT INTO vendas (data_hora, total, recebido, troco, metodo, itens_texto) VALUES (?, ?, ?, ?, ?, ?)", 
                               (data_venda, self.total_venda, recebido, troco, metodo, texto_cupom))
            
            self.win_pag.destroy()
            self.mostrar_e_imprimir_cupom(texto_cupom)
            self.limpar_caixa_pos_venda()
            self.atualizar_tabela_vendas()
            self.atualizar_lista_estoque()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro: {e}")

    def mostrar_e_imprimir_cupom(self, texto):
        win_cupom = tk.Toplevel(self.root)
        win_cupom.title("CUPOM")
        win_cupom.geometry("350x550")
        win_cupom.grab_set()

        txt_area = tk.Text(win_cupom, font=("Courier New", 11), width=32, height=22)
        txt_area.insert(tk.END, texto)
        txt_area.config(state=tk.DISABLED)
        txt_area.pack(padx=10, pady=10)

        def imprimir():
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w") as f:
                    f.write(texto)
                    path = f.name
                os.startfile(path, "print")
                win_cupom.destroy()
            except: messagebox.showerror("Erro", "Falha ao imprimir.")

        tk.Button(win_cupom, text="IMPRIMIR (ENTER)", bg="blue", fg="white", command=imprimir).pack(fill=tk.X, padx=20, pady=5)
        win_cupom.bind("<Return>", lambda e: imprimir())
        win_cupom.bind("<Escape>", lambda e: win_cupom.destroy())

    def remover_item(self):
        sel = self.tree_carrinho.selection()
        if not sel: return
        idx = self.tree_carrinho.index(sel)
        val = self.carrinho_dados.pop(idx)
        self.total_venda -= val['sub']
        self.tree_carrinho.delete(sel)
        self.lbl_total.config(text=f"R$ {self.total_venda:.2f}")

    def setup_estoque(self):
        frame = tk.LabelFrame(self.aba_estoque, text=" Gerenciar Produtos ", padx=10, pady=10)
        frame.pack(fill=tk.X, padx=10, pady=5)
        self.ents_est = {}
        campos = ["Cód. Barras", "Nome", "Qtd", "Preço"]
        for i, txt in enumerate(campos):
            tk.Label(frame, text=txt).grid(row=0, column=i*2)
            e = tk.Entry(frame); e.grid(row=0, column=i*2+1, padx=5); self.ents_est[txt] = e
        
        tk.Button(frame, text="Salvar", bg="blue", fg="white", command=self.salvar_no_estoque).grid(row=0, column=8, padx=5)
        tk.Button(frame, text="Remover Qtd", bg="orange", command=self.remover_estoque_manual).grid(row=0, column=9, padx=5)
        tk.Button(frame, text="Excluir", bg="#ef5350", fg="white", command=self.excluir_do_estoque).grid(row=0, column=10)

        self.tree_est = ttk.Treeview(self.aba_estoque, columns=("1", "2", "3", "4", "5"), show="headings")
        for i, c in enumerate(["ID", "Cod", "Nome", "Qtd", "Preço"]): self.tree_est.heading(str(i+1), text=c)
        self.tree_est.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.atualizar_lista_estoque()

    def salvar_no_estoque(self):
        try:
            with self.conectar() as conn:
                conn.execute("INSERT OR REPLACE INTO estoque (codigo_barras, nome, quantidade, preco_venda) VALUES (?,?,?,?)",
                    (self.ents_est["Cód. Barras"].get(), self.ents_est["Nome"].get(), int(self.ents_est["Qtd"].get()), float(self.ents_est["Preço"].get().replace(',','.'))))
            self.atualizar_lista_estoque()
            for e in self.ents_est.values(): e.delete(0, tk.END)
        except: messagebox.showerror("Erro", "Dados inválidos.")

    def atualizar_lista_estoque(self):
        for i in self.tree_est.get_children(): self.tree_est.delete(i)
        with self.conectar() as conn:
            for row in conn.execute("SELECT * FROM estoque"): self.tree_est.insert("", "end", values=row)

    def remover_estoque_manual(self):
        sel = self.tree_est.selection()
        if not sel: return
        item = self.tree_est.item(sel)['values']
        qtd = simpledialog.askinteger("Remover", f"Quantas unidades de '{item[2]}' retirar?")
        if qtd:
            with self.conectar() as conn:
                conn.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE codigo_barras = ?", (qtd, item[1]))
            self.atualizar_lista_estoque()

    def excluir_do_estoque(self):
        sel = self.tree_est.selection()
        if not sel: return
        item_id = self.tree_est.item(sel)['values'][0]
        if messagebox.askyesno("Confirmar", "Excluir permanentemente?"):
            with self.conectar() as conn:
                conn.execute("DELETE FROM estoque WHERE id = ?", (item_id,))
            self.atualizar_lista_estoque()

    def setup_historico(self):
        frame_filtros = tk.Frame(self.aba_historico, pady=10, padx=10); frame_filtros.pack(fill=tk.X)
        tk.Label(frame_filtros, text="Filtro Data:").pack(side=tk.LEFT)
        self.ent_busca_data = tk.Entry(frame_filtros); self.ent_busca_data.pack(side=tk.LEFT, padx=5)
        tk.Button(frame_filtros, text="Filtrar", bg="#1976d2", fg="white", command=self.filtrar_vendas).pack(side=tk.LEFT)
        tk.Button(frame_filtros, text="VER/IMPRIMIR NOTA", bg="orange", command=self.reimprimir_nota).pack(side=tk.RIGHT, padx=10)
        
        self.frame_estats = tk.Frame(self.aba_historico, pady=10); self.frame_estats.pack(fill=tk.X, padx=10)
        self.lbl_fat_total = self.criar_indicador(self.frame_estats, "FATURAMENTO", "#2e7d32", 0)
        self.lbl_vendas_qtd = self.criar_indicador(self.frame_estats, "VENDAS", "#1565c0", 1)
        self.lbl_ticket_medio = self.criar_indicador(self.frame_estats, "TICKET MEDIO", "#7b1fa2", 2)

        cols = ("ID", "Data/Hora", "Total", "Recebido", "Troco", "Metodo")
        self.tree_vendas = ttk.Treeview(self.aba_historico, columns=cols, show="headings")
        for col in cols: self.tree_vendas.heading(col, text=col)
        self.tree_vendas.pack(fill=tk.BOTH, expand=True, padx=10)
        self.atualizar_tabela_vendas()

    def criar_indicador(self, parent, titulo, cor, col):
        f = tk.Frame(parent, bg=cor, padx=15, pady=10); f.grid(row=0, column=col, padx=5, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(f, text=titulo, bg=cor, fg="white", font=("Arial", 9, "bold")).pack()
        lbl_valor = tk.Label(f, text="0.00", bg=cor, fg="white", font=("Arial", 14, "bold")); lbl_valor.pack()
        return lbl_valor

    def reimprimir_nota(self):
        sel = self.tree_vendas.selection()
        if not sel: return
        id_venda = self.tree_vendas.item(sel)['values'][0]
        with self.conectar() as conn:
            res = conn.execute("SELECT itens_texto FROM vendas WHERE id = ?", (id_venda,)).fetchone()
            if res: self.mostrar_e_imprimir_cupom(res[0])

    def atualizar_tabela_vendas(self):
        self.carregar_dados_vendas("SELECT id, data_hora, total, recebido, troco, metodo FROM vendas ORDER BY id DESC")

    def filtrar_vendas(self):
        d = self.ent_busca_data.get().strip()
        self.carregar_dados_vendas("SELECT id, data_hora, total, recebido, troco, metodo FROM vendas WHERE data_hora LIKE ? ORDER BY id DESC", (f"{d}%",))

    def carregar_dados_vendas(self, q, p=()):
        for i in self.tree_vendas.get_children(): self.tree_vendas.delete(i)
        tot, qtd = 0, 0
        with self.conectar() as conn:
            for r in conn.execute(q, p):
                self.tree_vendas.insert("", "end", values=r)
                tot += r[2]; qtd += 1
        self.lbl_fat_total.config(text=f"R$ {tot:.2f}")
        self.lbl_vendas_qtd.config(text=str(qtd))
        self.lbl_ticket_medio.config(text=f"R$ {tot/qtd:.2f}" if qtd > 0 else "0.00")

    def calc_troco_venda(self, e):
        try:
            recebido = float(self.ent_recebido.get().replace(',', '.'))
            troco = recebido - self.total_venda
            txt = f"Troco: R$ {troco:.2f}" if troco >= 0 else f"Faltam: R$ {abs(troco):.2f}"
            self.lbl_troco_win.config(text=txt, fg="green" if troco >= 0 else "red")
        except: pass

    def limpar_caixa_pos_venda(self):
        self.carrinho_dados = []
        self.total_venda = 0.0
        self.lbl_total.config(text="R$ 0.00")
        for i in self.tree_carrinho.get_children(): self.tree_carrinho.delete(i)
        self.ent_codigo_pdv.focus_set()

if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaSupermercado(root)
    root.mainloop()
    