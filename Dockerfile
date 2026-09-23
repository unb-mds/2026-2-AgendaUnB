FROM node:20-alpine
WORKDIR /app
# Copia apenas os arquivos de configuração de dependências primeiro ( otimização do cache do Docker )
COPY package.json package-lock.json* ./

# Instala as dependências
RUN npm install

# Copia o resto do código da aplicação
COPY . .

# Expõe a porta que o Vite usa
EXPOSE 5173

# Rodar o server dev 
CMD ["npm", "run", "dev", "--", "--host"]

