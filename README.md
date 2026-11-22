Simulador de Sistema Operacional

Etapa 01: Simulador de Sistema de Arquivos (OS)
Simulador em Python focado na camada lógica e física de um disco, demonstrando a estratégia de Alocação Indexada (i-node), mapeamento de blocos e cálculo de fragmentação interna/externa.

Etapa 02: Gerenciamento de Entrada e Saída (E/S) e Escalonamento de Disco

Criação de solicitações de E/S traduzidas em operações de disco, demonstração de ordenação e o atendimento de requisições de E/S na fila do disco, calculando o deslocamento total do braço, e também a implementação de abstração do armazenamento em arranjos de discos rígidos, ex: RAID.

Etapa 03: Criação de login, permissionamento e privilégios de usuário, e também criptografia e varredura através de antivirus simulado.

O sistema agora consegue diferenciar a execução do simulador entre Modo Usuário e Modo Kernel (Superusuário/Root). Operações críticas do sistema devem exigir privilégios elevados.Cadastro de múltiplos usuários e grupos. Armazenamento seguro de senhas utilizando rotinas de hashing (ex.: SHA-256 ou simulação equivalente com salt). Matriz de Acesso ou Lista de Controle de Acesso (ACL) associada aos arquivos/diretórios (permissões de leitura, escrita e execução: rwx para Proprietário, Grupo e Outros). Suporte a criptografia de dados em repouso (conteúdo criptografado antes da gravação no bloco físico).
(Anti-Vírus Simulado): Rotina de auditoria e varredura do Sistema de Arquivos capaz de checar a integridade dos blocos e identificar alterações não autorizadas ou assinaturas maliciosas.

Etapa 04: Implentação de Gerencimento de memória, análise e ocupação de processos e paginação de memória (22/11)

As principais melhorias introduzem um gerenciamento de memória híbrida e uma interface interativa reformulada. O simulador agora divide a RAM entre uma área reservada fixa de 4 MB (com alocação contígua para processos críticos, diagnóstico de fragmentação externa e compactação) e uma memória virtual paginada de 4 KB para processos comuns, contemplando análise de fragmentação interna, tradução de endereços, page faults, swap e substituição de páginas (LRU, Segunda Chance e FIFO). Além do controle de processos e relatórios de ocupação. 
Já a interface foi reorganizada em menus numerados com navegação instantânea sem Enter onde o usuário navega digitando números, preenchimento guiado passo a passo e saída sob demanda, exibindo detalhes extras apenas quando solicitado ou por meio do comando status.
