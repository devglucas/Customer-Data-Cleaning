# Relatório de consolidação de clientes

_Gerado automaticamente por `python main.py`._

## 1. Visão geral

Fontes: CRM 4.738 · App 2.759 · Lojas 1.284 registros.

| Etapa | Quantidade |
|---|---|
| Registros brutos (CRM + App + Lojas) | 8.781 |
| Registros rejeitados (teste / sem identificação) | 14 |
| Registros padronizados | 8.767 |
| Clientes únicos (golden record) | 6.004 |
| Registros duplicados eliminados | 2.763 |
| Clientes elegíveis para marketing (opt-in + e-mail) | 2.951 |

## 2. Qualidade das fontes

### Preenchimento bruto (antes da limpeza)

| coluna | crm | app | loja |
|---|---|---|---|
| nome | 100,0 | 100,0 | 100,0 |
| cpf | 100,0 | 88,6 | 94,4 |
| data_nascimento | 100,0 | 92,3 | 95,2 |
| genero | 94,6 | 94,3 | 0,0 |
| email | 94,9 | 94,7 | 95,6 |
| telefone | 95,0 | 94,6 | 95,9 |
| endereco | 100,0 | 0,0 | 0,0 |
| logradouro | 0,0 | 84,8 | 0,0 |
| numero | 0,0 | 84,8 | 0,0 |
| complemento | 0,0 | 24,1 | 0,0 |
| bairro | 100,0 | 84,8 | 0,0 |
| cidade | 100,0 | 84,8 | 100,0 |
| uf | 96,9 | 84,8 | 0,0 |
| cep | 100,0 | 84,8 | 0,0 |
| opt_in_marketing | 90,2 | 100,0 | 74,9 |
| data_atualizacao | 100,0 | 100,0 | 100,0 |

### Valores válidos após a padronização

![Qualidade por fonte](charts/01_qualidade_por_fonte.png)

| campo | crm | app | loja |
|---|---|---|---|
| CPF | 95,9 | 88,6 | 94,3 |
| Data de nascimento | 99,1 | 92,3 | 95,2 |
| Gênero | 92,6 | 88,4 | 0,0 |
| E-mail | 93,1 | 92,6 | 85,0 |
| Telefone | 95,0 | 93,8 | 95,9 |
| Endereço | 100,0 | 84,8 | 0,0 |
| CEP | 100,0 | 84,8 | 0,0 |
| Cidade | 100,0 | 84,8 | 100,0 |

### Situação do CPF

| cpf_status | crm | app | loja | total |
|---|---|---|---|---|
| ausente | 0 | 314 | 72 | 386 |
| ilegivel | 99 | 0 | 0 | 99 |
| invalido | 95 | 0 | 1 | 96 |
| valido | 4.530 | 2.445 | 1.211 | 8.186 |
| total | 4.724 | 2.759 | 1.284 | 8.767 |

## 3. Correções automáticas

![Correções](charts/02_correcoes_por_fonte.png)

| correcao | crm | app | loja | total |
|---|---|---|---|---|
| nome_reacentuado | 1.907 | 0 | 0 | 1.907 |
| telefone_nono_digito | 802 | 0 | 0 | 802 |
| telefone_ddd_inferido | 289 | 110 | 63 | 462 |
| email_dominio | 227 | 139 | 52 | 418 |
| cep_zero_restaurado | 269 | 0 | 0 | 269 |
| cidade_apelido | 123 | 55 | 31 | 209 |
| cpf_zeros_restaurados | 67 | 0 | 74 | 141 |
| nome_mojibake | 0 | 47 | 0 | 47 |
| nascimento_implausivel | 44 | 0 | 0 | 44 |

## 4. Deduplicação

### Pares encontrados por regra

| regra | pares | similaridade_media | similaridade_minima |
|---|---|---|---|
| cpf | 2.857 | 0,991 | 0,765 |
| email_e_nome | 1.968 | 0,991 | 0,889 |
| telefone_e_nome | 2.139 | 0,990 | 0,900 |
| nascimento_e_nome | 3.081 | 0,991 | 0,889 |

### Avaliação contra o gabarito

![Estratégias](charts/03_estrategias_deduplicacao.png)

| estrategia | pares_previstos | pares_reais | pares_corretos | precisao_pct | recall_pct | f1_pct | clientes_encontrados | pessoas_reais | pessoas_divididas_em_2_ou_mais_clientes | clientes_misturando_pessoas |
|---|---|---|---|---|---|---|---|---|---|---|
| cpf | 2.857 | 3.332 | 2.857 | 100,00 | 85,74 | 92,33 | 6.362 | 6.000 | 359 | 0 |
| cpf + email_e_nome | 3.167 | 3.332 | 3.167 | 100,00 | 95,05 | 97,46 | 6.125 | 6.000 | 125 | 0 |
| cpf + email_e_nome + telefone_e_nome | 3.289 | 3.332 | 3.289 | 100,00 | 98,71 | 99,35 | 6.037 | 6.000 | 37 | 0 |
| cpf + email_e_nome + telefone_e_nome + nascimento_e_nome | 3.328 | 3.332 | 3.328 | 100,00 | 99,88 | 99,94 | 6.004 | 6.000 | 4 | 0 |

### Sobreposição entre fontes

![Sobreposição](charts/04_sobreposicao_fontes.png)

| fontes | clientes | pct |
|---|---|---|
| crm | 2.655 | 44,2 |
| app, crm | 1.171 | 19,5 |
| app | 960 | 16,0 |
| crm, loja | 354 | 5,9 |
| loja | 316 | 5,3 |
| app, crm, loja | 305 | 5,1 |
| app, loja | 243 | 4,0 |

| registros_por_cliente | clientes |
|---|---|
| 1 | 3.756 |
| 2 | 1.782 |
| 3 | 418 |
| 4 | 47 |
| 5 | 1 |

## 5. Golden record

![Ganho de sobrevivência](charts/05_ganho_sobrevivencia.png)

| campo | so_registro_mais_recente_pct | cadastro_final_pct | ganho_pp |
|---|---|---|---|
| CPF | 93,7 | 96,3 | 2,6 |
| Data de nascimento | 96,5 | 97,9 | 1,4 |
| Gênero | 79,7 | 88,5 | 8,8 |
| E-mail | 91,9 | 95,4 | 3,5 |
| Telefone | 94,7 | 96,6 | 1,9 |
| Endereço | 83,3 | 91,7 | 8,4 |
| CEP | 83,3 | 91,7 | 8,4 |
| Cidade | 95,6 | 97,8 | 2,2 |

### Acurácia por campo (versus dado real atual)

| campo | preenchido_pct | correto_quando_preenchido_pct |
|---|---|---|
| nome | 100,00 | 94,72 |
| cpf | 96,29 | 100,00 |
| data_nascimento | 97,87 | 100,00 |
| genero | 88,54 | 100,00 |
| email | 95,39 | 99,06 |
| telefone | 96,59 | 99,40 |
| cidade | 97,78 | 100,00 |
| uf | 97,78 | 100,00 |
| cep | 91,69 | 98,53 |
| opt_in_marketing | 100,00 | 96,94 |

## 6. Validações

**12 de 16 regras passaram**; todas as falhas restantes são alertas.

| tabela | regra | severidade | registros_com_falha | passou |
|---|---|---|---|---|
| clientes | cliente_id único | critica | 0 | sim |
| clientes | CPF único entre clientes | critica | 0 | sim |
| clientes | CPF válido quando preenchido | critica | 0 | sim |
| clientes | e-mail válido quando preenchido | critica | 0 | sim |
| clientes | telefone válido quando preenchido | critica | 0 | sim |
| clientes | CEP válido quando preenchido | critica | 0 | sim |
| clientes | UF válida quando preenchida | critica | 0 | sim |
| clientes | idade entre 16 e 110 anos | critica | 0 | sim |
| clientes | nome preenchido | critica | 0 | sim |
| registros | todo registro pertence a um cliente | critica | 0 | sim |
| registros | soma de qtd_registros = total de registros | critica | 0 | sim |
| registros | nenhum cliente reúne CPFs diferentes | critica | 0 | sim |
| clientes | cliente com CPF | alerta | 223 | não |
| clientes | cliente com e-mail ou telefone | alerta | 13 | não |
| clientes | cliente com data de nascimento | alerta | 128 | não |
| clientes | cliente com endereço | alerta | 499 | não |

## 7. Perfil da base consolidada

![Perfil](charts/06_perfil_clientes.png)

| faixa_etaria | F | M | Não informado | opt_in_pct |
|---|---|---|---|---|
| 16-24 | 94 | 86 | 21 | 50,2 |
| 25-34 | 699 | 563 | 158 | 53,6 |
| 35-44 | 877 | 650 | 198 | 49,0 |
| 45-54 | 581 | 500 | 135 | 53,0 |
| 55-64 | 350 | 282 | 73 | 48,9 |
| 65+ | 296 | 243 | 70 | 53,0 |

| uf | clientes | opt_in_pct | completude_media_pct |
|---|---|---|---|
| SP | 2.726 | 51,0 | 95,4 |
| RJ | 854 | 52,1 | 95,5 |
| MG | 636 | 51,6 | 95,5 |
| PR | 354 | 51,1 | 96,3 |
| RS | 333 | 48,3 | 94,1 |
| DF | 232 | 48,7 | 94,6 |
| BA | 207 | 55,1 | 95,8 |
| GO | 184 | 50,0 | 96,0 |
| PE | 177 | 55,4 | 94,7 |
| SC | 168 | 54,8 | 94,0 |
| ND | 133 | 55,6 | 55,8 |
