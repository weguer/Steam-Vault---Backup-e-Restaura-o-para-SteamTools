# Steam Vault - Backup e Restauração para Steam (Fork com Google Drive)

Este é um fork do [Steam Vault original](https://github.com/PedroMerlini/Steam-Vault---Backup-e-Restaura-o-para-SteamTools) com integração completa do Google Drive.

## ✨ Novidades nesta versão

- ✅ **Integração completa com Google Drive**
- ✅ Backup automático para nuvem
- ✅ Restauração de backups armazenados no Google Drive
- ✅ Botão de parar backup/restauração
- ✅ Interface aprimorada com guias separadas
- ✅ Substituição automática de arquivos

## 🚀 Funcionalidades

### Local
- Backup tradicional para diretório local
- Restauração de backups locais
- Interface intuitiva

### Google Drive ☁️
- Backup direto para Google Drive
- Restauração de backups da nuvem
- Gerenciamento de credenciais OAuth 2.0
- Controle de interrupção durante operações

## ⚙️ Configuração do Google Drive

Para usar a integração com Google Drive, você precisa configurar as credenciais da API:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Habilite a API do Google Drive
4. Crie credenciais OAuth 2.0 do tipo "Aplicativo para Web"
5. Adicione as URLs de redirecionamento (veja example.env)
6. Baixe o arquivo JSON com as credenciais
7. No aplicativo, vá em Configurações > Google Drive
8. Selecione o arquivo de credenciais baixado
9. Autorize o acesso quando solicitado

### Modo Desenvolvimento
Para uso em modo dev, é necessário ter o arquivo `.env` na pasta raiz com as configurações adequadas.

### Alternativa
Se não quiser utilizar o Google Drive integrado, pode montar o Google Drive com algum outro aplicativo no computador e utilizar a versão local selecionando o diretório montado.

## 📋 Requisitos

- Python 3.8+
- PyQt6
- Google API Client (google-api-python-client)
- Google Auth (google-auth-oauthlib)

## 🔧 Instalação

```bash
python Steam.vault.v0.3.py
```

## 📄 Licença

MIT - Veja o arquivo LICENSE para detalhes.

---

**Nota**: Este é um fork com melhorias adicionais. O projeto original pode ser encontrado [aqui](https://github.com/PedroMerlini/Steam-Vault---Backup-e-Restaura-o-para-SteamTools).
