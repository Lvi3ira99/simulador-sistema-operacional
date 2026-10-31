import math

class Disk:
    def __init__(self, total_blocks=16, block_size=4096):
        self.total_blocks = total_blocks
        self.block_size = block_size
        self.free_count = total_blocks
        # Representação física do disco
        self.blocks = [{"type": "LIVRE", "info": ""} for _ in range(total_blocks)]

    def allocate_blocks(self, count):
        """Busca blocos livres e os aloca (Alocação Indexada não exige que sejam contíguos)"""
        if count > self.free_count:
            return None # Espaço insuficiente
        
        allocated = []
        for i in range(self.total_blocks):
            if self.blocks[i]["type"] == "LIVRE":
                allocated.append(i)
                if len(allocated) == count:
                    break
        
        self.free_count -= len(allocated)
        return allocated

    def free_blocks(self, block_indices):
        """Libera os blocos especificados"""
        for i in block_indices:
            self.blocks[i] = {"type": "LIVRE", "info": ""}
            self.free_count += 1

class Node:
    """Representa um Arquivo ou Diretório na Árvore Hierárquica"""
    def __init__(self, name, is_dir, parent=None, size_bytes=0):
        self.name = name
        self.is_dir = is_dir
        self.parent = parent
        self.children = {}
        self.size_bytes = size_bytes
        self.inode_block = None
        self.data_blocks = []
        self.internal_frag = 0

class FileSystem:
    def __init__(self):
        self.disk = Disk(total_blocks=16, block_size=4096)
        self.root = Node("/", is_dir=True)
        
        # Alocando um i-node para o diretório raiz para simular a tabela
        root_blocks = self.disk.allocate_blocks(1)
        self.root.inode_block = root_blocks[0]
        self.disk.blocks[self.root.inode_block] = {
            "type": "[INODE_RAIZ]", 
            "info": "Diretório '/'"
        }

    def _resolve_path(self, path):
        """Navega na árvore e retorna o nó correspondente ao caminho"""
        if path == "/": return self.root
        curr = self.root if path.startswith("/") else self.root # Simplificação para caminhos absolutos
        parts = [p for p in path.split("/") if p]
        
        for part in parts:
            if part in curr.children:
                curr = curr.children[part]
            else:
                return None, part, curr # Retorna o nó pai caso o filho não exista
        return curr, None, None

    def mkdir(self, path):
        """CRUD - Create: Cria um diretório"""
        node, missing, parent = self._resolve_path(path)
        if node:
            print(f"Erro: O diretório '{path}' já existe.")
            return
        
        new_dir = Node(missing, is_dir=True, parent=parent)
        parent.children[missing] = new_dir
        print(f"> Diretório '{path}' criado com sucesso.")

    def create_file(self, path, size_kb):
        """CRUD - Create: Cria um arquivo com tamanho específico"""
        node, missing, parent = self._resolve_path(path)
        if node:
            print(f"Erro: O arquivo '{path}' já existe.")
            return
        
        size_bytes = int(size_kb * 1024)
        data_blocks_needed = math.ceil(size_bytes / self.disk.block_size)
        total_blocks_needed = data_blocks_needed + 1 # +1 para o bloco de i-node
        
        blocks = self.disk.allocate_blocks(total_blocks_needed)
        if not blocks:
            print("Erro: Espaço insuficiente no disco.")
            return

        new_file = Node(missing, is_dir=False, parent=parent, size_bytes=size_bytes)
        new_file.inode_block = blocks[0]
        new_file.data_blocks = blocks[1:]
        parent.children[missing] = new_file

        # Gravando no Disco
        tag = missing.split('.')[0].upper()
        self.disk.blocks[new_file.inode_block] = {
            "type": f"[INODE_{tag}]", 
            "info": f"Arquivo '{path}'"
        }

        bytes_remaining = size_bytes
        for i, b_idx in enumerate(new_file.data_blocks):
            used_in_block = min(bytes_remaining, self.disk.block_size)
            bytes_remaining -= used_in_block
            self.disk.blocks[b_idx] = {
                "type": "[DADO]",
                "info": f"'{path}' (Bloco {i+1} - {used_in_block} bytes ocupados)"
            }
            # Cálculo da fragmentação interna no último bloco
            if bytes_remaining == 0:
                new_file.internal_frag = self.disk.block_size - used_in_block

        print(f"> Arquivo '{path}' ({size_kb}KB) criado com sucesso.")

    def rm(self, path):
        """CRUD - Delete: Remove arquivo ou diretório"""
        node, _, _ = self._resolve_path(path)
        if not node or node.name == "/":
            print("Erro: Caminho inválido.")
            return
        
        # Libera os blocos se for arquivo
        if not node.is_dir:
            blocks_to_free = [node.inode_block] + node.data_blocks
            self.disk.free_blocks(blocks_to_free)
        
        del node.parent.children[node.name]
        print(f"> '{path}' deletado com sucesso.")

    def tree(self):
        """CRUD - Read: Exibe a hierarquia visualmente"""
        print("\n[ÁRVORE DO SISTEMA DE ARQUIVOS]")
        print("/")
        self._print_tree(self.root, "", True)
        print()

    def _print_tree(self, node, prefix, is_last):
        if node.name != "/":
            marker = "└── " if is_last else "├── "
            if node.is_dir:
                print(f"{prefix}{marker}{node.name}/ [DIR]")
            else:
                size_kb = node.size_bytes / 1024
                size_str = f"{int(size_kb)} KB" if size_kb.is_integer() else f"{size_kb:.1f} KB"
                print(f"{prefix}{marker}{node.name} ({size_str}) [ARQ]")
            prefix += "    " if is_last else "│   "

        children = list(node.children.values())
        for i, child in enumerate(children):
            self._print_tree(child, prefix, i == len(children) - 1)

    def fs_status(self):
        """Diagnóstico do Disco"""
        print(f"Tamanho do Bloco de Disco: {self.disk.block_size // 1024} KB | "
              f"Total de Blocos: {self.disk.total_blocks} ({self.disk.total_blocks * self.disk.block_size // 1024} KB)\n")
        print("[MAPA DE ALOCAÇÃO DO DISCO (Indexado)]")
        
        i = 0
        while i < self.disk.total_blocks:
            if self.disk.blocks[i]["type"] == "LIVRE":
                start = i
                while i < self.disk.total_blocks and self.disk.blocks[i]["type"] == "LIVRE":
                    i += 1
                end = i - 1
                if start == end:
                    print(f"Bloco {start:02d}               : [LIVRE]")
                else:
                    print(f"Bloco {start:02d}..{end:02d}           : [LIVRE]")
            else:
                b = self.disk.blocks[i]
                print(f"Bloco {i:02d} {b['type']:13s} : {b['info']}")
                i += 1

        print("\n--- RELATÓRIO DE FRAGMENTAÇÃO ---")
        total_internal_frag = 0
        files = self._get_all_files(self.root)
        
        for f in files:
            alocado = len(f.data_blocks) * self.disk.block_size
            total_internal_frag += f.internal_frag
            perc = (f.internal_frag / self.disk.block_size) * 100 if f.internal_frag > 0 else 0
            
            print(f"Arquivo '{f.name}':")
            print(f"  Tamanho Real          : {f.size_bytes} bytes ({f.size_bytes//1024} KB)")
            print(f"  Espaço Alocado (Dados): {alocado} bytes ({len(f.data_blocks)} blocos)")
            print(f"  Fragmentação Interna  : {f.internal_frag} bytes ({perc:.0f}% de desperdício no último bloco)")
            
        print(f"Fragmentação Externa    : 0 bytes (Evitada pelo modelo de i-node indexado)")
        print(f"Necessidade de Compactação: NÃO (Blocos alocados via i-node indexado permitem fragmentação física sem impacto lógico)")
        print("-" * 33 + "\n")

    def _get_all_files(self, node):
        files = []
        if not node.is_dir:
            files.append(node)
        for child in node.children.values():
            files.extend(self._get_all_files(child))
        return files


# -------------------------------------------------------------
# EXECUÇÃO DO SIMULADOR (Demonstração Automática)
# -------------------------------------------------------------
if __name__ == "__main__":
    fs = FileSystem()
    print("Simulador de Arquivos (i-node). Digite 'ajuda' para ver os comandos.")
    
    while True:
        try:
            entrada = input("\nsimulador> ").strip().split()
            if not entrada:
                continue
                
            comando = entrada[0].lower()
            
            if comando == "sair":
                print("Encerrando simulador...")
                break
            elif comando == "mkdir" and len(entrada) == 2:
                fs.mkdir(entrada[1])
            elif comando == "create" and len(entrada) == 3:
                fs.create_file(entrada[1], float(entrada[2]))
            elif comando == "rm" and len(entrada) == 2:
                fs.rm(entrada[1])
            elif comando == "tree":
                fs.tree()
            elif comando == "status":
                fs.fs_status()
            elif comando == "ajuda":
                print("Comandos disponíveis:")
                print("  mkdir <caminho>           - Cria um diretório (ex: mkdir /docs)")
                print("  create <caminho> <tamanho>- Cria um arquivo em KB (ex: create /docs/arq.txt 5)")
                print("  rm <caminho>              - Deleta um arquivo/diretório (ex: rm /docs/arq.txt)")
                print("  tree                      - Mostra a árvore de diretórios")
                print("  status                    - Mostra o mapa do disco e fragmentação")
                print("  sair                      - Fecha o simulador")
            else:
                print("Comando inválido ou incompleto. Digite 'ajuda'.")
        except Exception as e:
            print(f"Erro ao processar comando: {e}")