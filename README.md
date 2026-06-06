# Higgsfield — Projet UGC

Configuration du serveur **MCP Higgsfield** (génération d'images / vidéos IA, pubs UGC) pour ce dépôt.

## Serveur MCP

Le fichier [`.mcp.json`](./.mcp.json) déclare le serveur MCP officiel hébergé (scope projet) :

```json
{
  "mcpServers": {
    "higgsfield": {
      "type": "http",
      "url": "https://mcp.higgsfield.ai/mcp"
    }
  }
}
```

## Activation

À la racine du dépôt, avec **Claude Code** :

1. Ouvrez le projet — Claude Code détecte `.mcp.json` et propose d'approuver le serveur.
2. Au premier appel, une fenêtre **OAuth** s'ouvre : connectez-vous à votre compte Higgsfield.
3. Vérifiez :

   ```bash
   claude mcp list   # ou la commande /mcp
   ```

> ⚠️ L'authentification OAuth nécessite un navigateur : lancez-la depuis votre **machine locale**.

## Alternative — CLI (scope utilisateur)

Pour rendre le serveur disponible dans tous vos projets :

```bash
claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp
```

## Liens

- Higgsfield MCP (officiel) : https://higgsfield.ai/mcp
