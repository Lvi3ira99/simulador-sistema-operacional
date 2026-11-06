import math
from os import path

# =====================================================================
# CAMADA FÍSICA: DISCO LÓGICO E HARDWARE
# =====================================================================
class Disk:
    """Representa a visão lógica do disco gerenciada pelo Sistema de Arquivos"""
    def __init__(self, total_blocks=32, block_size=4096):
        self.total_blocks = total_blocks
        self.block_size = block_size
        self.free_count = total_blocks
        self.blocks = [{"type": "LIVRE", "info": ""} for _ in range(total_blocks)]

    def allocate_blocks(self, count):
        """Busca blocos livres e os aloca (Alocação Indexada não contígua)"""
        if count > self.free_count:
            return None 
        
        allocated = []
        for i in range(self.total_blocks):
            if self.blocks[i]["type"] == "LIVRE":
                allocated.append(i)
                if len(allocated) == count:
                    break
        
        self.free_count -= len(allocated)
        return allocated

    def free_blocks(self, block_indices):
        for i in block_indices:
            self.blocks[i] = {"type": "LIVRE", "info": ""}
            self.free_count += 1

class DiskScheduler:
    """Simula o firmware/SO ordenando a fila de requisições de E/S (SSTF)"""
    def __init__(self, current_head_position=15):
        # Posição inicial arbitrária da cabeça de leitura
        self.head_position = current_head_position

    def schedule_sstf(self, requests_queue):
        if not requests_queue:
            return

        print(f"\n[E/S] Requisições pendentes nas trilhas (blocos físicos): {requests_queue}")
        print(f"Posição atual da cabeça de leitura: Trilha {self.head_position}")
        print("--- ESCALONAMENTO DE DISCO: SSTF (Shortest Seek Time First) ---")

        pending = list(requests_queue)
        current_pos = self.head_position
        path = []
        math_steps = []
        total_movement = 0

        while pending:
            # Encontra a trilha mais próxima
            closest_track = min(pending, key=lambda track: abs(track - current_pos))
            distance = abs(closest_track - current_pos)
            
            path.append(str(closest_track))
            math_steps.append(f"|{current_pos}-{closest_track}|")
            total_movement += distance
            
            current_pos = closest_track
            pending.remove(closest_track)

        initial_pos = self.head_position
        self.head_position = current_pos

        print(f"Ordem de Atendimento  : {initial_pos} -> " + " -> ".join(path))
        print(f"Deslocamento da Cabeça: " + " + ".join(math_steps))
        print(f"Total de Movimento    : {total_movement} trilhas deslocadas\n")

class RAID5Controller:
    """Abstrai discos físicos implementando RAID 5 (Striping + Paridade)"""
    def __init__(self, num_disks=3):
        self.num_disks = num_disks
        self.physical_disks = {1: {}, 2: {}, 3: {}}

    def write_data(self, filename, data_blocks):
        print(f"[RAID 5] Gravando dados físicos de '{filename}' nos discos...")
        
        # Agrupa os blocos de dados de 2 em 2 (pois o 3º disco guarda a paridade)
        for i in range(0, len(data_blocks), 2):
            b1 = data_blocks[i]
            # Se houver um número ímpar de blocos, o segundo será Nulo
            b2 = data_blocks[i+1] if i+1 < len(data_blocks) else "NULO"
            
            # Distribui nos discos (Striping)
            self.physical_disks[1][b1] = f"Dado {filename} (Bloco Lógico {b1})"
            self.physical_disks[2][b2] = f"Dado {filename} (Bloco Lógico {b2})"
            
            # Paridade no 3º Disco (XOR Lógico)
            self.physical_disks[3][f"P({b1},{b2})"] = f"XOR({b1}, {b2})"
            
            print(f" -> Disco 1: [Bloco {b1}] | Disco 2: [Bloco {b2}] | Disco 3: [PARIDADE XOR({b1},{b2})]")

    def simulate_failure(self):
        print("\n[RAID 5 - TESTE DE FALHA SIMULADO]")
        print("- Falha catastrófica forçada no Disco 2!")
        self.physical_disks[2].clear() # Queima o disco 2

        print("- Iniciando processo de Reconstrução (Rebuild)...")
        print("- Lendo Dados do Disco 1 e Paridades do Disco 3...")
        print("- Calculando via XOR (Disco 1 XOR Disco 3) = Dados do Disco 2...")
        print("- Reconstrução concluída com sucesso! Disco 2 online novamente.\n")

# =====================================================================
# CAMADA LÓGICA: SISTEMA DE ARQUIVOS
# =====================================================================
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
        self.disk = Disk(total_blocks=32, block_size=4096)
        self.scheduler = DiskScheduler()
        self.raid = RAID5Controller()
        
        self.root = Node("/", is_dir=True)
        root_blocks = self.disk.allocate_blocks(1)
        self.root.inode_block = root_blocks[0]
        self.disk.blocks[self.root.inode_block] = {"type": "[INODE_RAIZ]", "info": "Diretório '/'"}

    def _resolve_path(self, path):
        if path == "/": return self.root
        curr = self.root
        parts = [p for p in path.split("/") if p]
        
        for part in parts:
            if part in curr.children:
                curr = curr.children[part]
            else:
                return None, part, curr
        return curr, None, None

    def mkdir(self, path):
        node, missing, parent = self._resolve_path(path)
        if node:
            print(f"Erro: O diretório '{path}' já existe.")
            return
        
        new_dir = Node(missing, is_dir=True, parent=parent)
        parent.children[missing] = new_dir
        print(f"> Diretório '{path}' criado com sucesso.")

    def create_file(self, path, size_kb):
        """CRUD - Create Integrado com E/S e RAID"""
        node, missing, parent = self._resolve_path(path)
        if node:
            print(f"Erro: O arquivo '{path}' já existe.")
            return
        
        # 1. CÁLCULO LÓGICO DE ARMAZENAMENTO
        size_bytes = int(size_kb * 1024)
        data_blocks_needed = math.ceil(size_bytes / self.disk.block_size)
        total_blocks_needed = data_blocks_needed + 1 # +1 do i-node
        
        blocks = self.disk.allocate_blocks(total_blocks_needed)
        if not blocks:
            print("Erro: Espaço insuficiente no disco lógico.")
            return

        # 2. CRIAÇÃO DO NÓ E ALOCAÇÃO LÓGICA (I-NODE)
        new_file = Node(missing, is_dir=False, parent=parent, size_bytes=size_bytes)
        new_file.inode_block = blocks[0]
        new_file.data_blocks = blocks[1:]
        parent.children[missing] = new_file

        tag = missing.split('.')[0].upper()
        self.disk.blocks[new_file.inode_block] = {"type": f"[INODE_{tag}]", "info": f"Arquivo '{path}'"}

        bytes_remaining = size_bytes
        for i, b_idx in enumerate(new_file.data_blocks):
            used_in_block = min(bytes_remaining, self.disk.block_size)
            bytes_remaining -= used_in_block
            self.disk.blocks[b_idx] = {"type": "[DADO]", "info": f"'{path}' ({used_in_block} bytes)"}
            if bytes_remaining == 0:
                new_file.internal_frag = self.disk.block_size - used_in_block

        # 3. INTEGRAÇÃO: ACIONANDO O HARDWARE (E/S E RAID)
        print("\n[SO] Traduzindo requisição lógica em operações físicas...")
        
        # Escalonador define o movimento mecânico da agulha para os blocos de dados alocados
        self.scheduler.schedule_sstf(new_file.data_blocks)
        
        # RAID espalha fisicamente os dados nos HDDs reais
        self.raid.write_data(missing, new_file.data_blocks)

        print(f"\n> Sucesso! Arquivo '{path}' ({size_kb}KB) criado, escalonado e gravado no RAID.")

    def tree(self):
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
                print(f"{prefix}{marker}{node.name} ({size_kb:.1f} KB) [ARQ]")
            prefix += "    " if is_last else "│   "

        children = list(node.children.values())
        for i, child in enumerate(children):
            self._print_tree(child, prefix, i == len(children) - 1)

# =====================================================================
# CLI - INTERAÇÃO COM O USUÁRIO
# =====================================================================
if __name__ == "__main__":
    fs = FileSystem()
    print("=== Simulador de SO: FS + E/S + RAID ===")
    print("\nDigite 'ajuda' para ver os comandos.")
    
    while True:
        try:
            entrada = input("\nsimulador> ").strip().split()
            if not entrada: continue
                
            comando = entrada[0].lower()
            
            if comando == "sair":
                print("Encerrando simulador de SO...")
                break
            elif comando == "mkdir" and len(entrada) == 2:
                fs.mkdir(entrada[1])
            elif comando == "create" and len(entrada) == 3:
                # O comando create agora faz TODAS as etapas do SO!
                fs.create_file(entrada[1], float(entrada[2]))
            elif comando == "tree":
                fs.tree()
            elif comando == "fail_disk":
                # Testa a recuperação do RAID 5
                fs.raid.simulate_failure()
            elif comando == "ajuda":
                print("Comandos disponíveis:")
                print("  mkdir <caminho>          - Cria pasta (ex: mkdir /docs)")
                print("  create <caminho> <KB>    - Cria arquivo (Aloca i-node + SSTF + RAID)")
                print("                             Ex: create /docs/video.mp4 15")
                print("  fail_disk                - Simula quebra e reconstrução no RAID 5")
                print("  tree                     - Mostra árvore de diretórios")
                print("  sair                     - Fecha simulador")
            else:
                print("Comando inválido. Digite 'ajuda'.")
        except Exception as e:
            print(f"Erro ao processar comando: {e}")
