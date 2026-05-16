export interface TagConfig {
  label: string
  value: string
  subtags: SubtagConfig[]
}

export interface SubtagConfig {
  label: string
  value: string
}

export const TAG_CONFIG: Record<string, TagConfig> = {
  PET: {
    label: 'PET',
    value: 'PET',
    subtags: [
      { label: 'Gatos', value: 'gatos' },
      { label: 'Cães', value: 'caes' },
      { label: 'Ração', value: 'racao' },
      { label: 'Higiene', value: 'higiene' },
      { label: 'Brinquedos', value: 'brinquedos' },
      { label: 'Acessórios', value: 'acessorios' },
      { label: 'Saúde', value: 'saude' },
    ],
  },
  E: {
    label: 'ELETRÔNICOS',
    value: 'E',
    subtags: [
      { label: 'Smartphones', value: 'smartphones' },
      { label: 'Áudio', value: 'audio' },
      { label: 'Computadores', value: 'computadores' },
      { label: 'TVs', value: 'tv' },
      { label: 'Games', value: 'games' },
      { label: 'Câmeras', value: 'cameras' },
      { label: 'Smartwatch', value: 'smartwatch' },
      { label: 'Acessórios', value: 'acessorios' },
    ],
  },
  CD: {
    label: 'CASA & DECORAÇÃO',
    value: 'CD',
    subtags: [
      { label: 'Banheiro', value: 'banheiro' },
      { label: 'Sala', value: 'sala' },
      { label: 'Quarto', value: 'quarto' },
      { label: 'Cozinha', value: 'cozinha' },
      { label: 'Garagem', value: 'garagem' },
      { label: 'Corredor', value: 'corredor' },
      { label: 'Sacada', value: 'sacada' },
      { label: 'Área de Serviço', value: 'area-servico' },
    ],
  },
  ME: {
    label: 'MODA',
    value: 'ME',
    subtags: [
      { label: 'Feminino', value: 'feminino' },
      { label: 'Masculino', value: 'masculino' },
      { label: 'Calçados', value: 'calcados' },
      { label: 'Acessórios', value: 'acessorios' },
      { label: 'Bolsas', value: 'bolsas' },
      { label: 'Relógios', value: 'relogios' },
      { label: 'Infantil', value: 'infantil' },
    ],
  },
  ES: {
    label: 'ESPORTES',
    value: 'ES',
    subtags: [
      { label: 'Futebol', value: 'futebol' },
      { label: 'Corrida', value: 'corrida' },
      { label: 'Academia', value: 'academia' },
      { label: 'Natação', value: 'natacao' },
      { label: 'Ciclismo', value: 'ciclismo' },
      { label: 'Tênis', value: 'tenis' },
      { label: 'Esportes Radicais', value: 'esportes-radicais' },
      { label: 'Acessórios', value: 'acessorios' },
    ],
  },
}
