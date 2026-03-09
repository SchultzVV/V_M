// search.js - Sistema de busca reutilizável

let allProducts = []; // Variável global para armazenar todos os produtos
let currentSearchTerm = ''; // Termo de busca atual

function getNumericPrice(priceStr) {
  return parseFloat(priceStr.replace("R$", "").replace(",", ".").trim());
}

function getDiscountPercentage(product) {
  if (!product.oldPrice || product.oldPrice === product.price) return 0;
  const oldPrice = getNumericPrice(product.oldPrice);
  const currentPrice = getNumericPrice(product.price);
  if (oldPrice > currentPrice) {
    return Math.round((1 - currentPrice / oldPrice) * 100);
  }
  return 0;
}

function updateResultsCount(count, total, searchTerm = '') {
  const resultsDiv = document.getElementById('resultsCount');
  if (!resultsDiv) return;
  
  if (searchTerm) {
    resultsDiv.textContent = `🔍 ${count} produto${count !== 1 ? 's' : ''} encontrado${count !== 1 ? 's' : ''} para "${searchTerm}"`;
  } else if (count !== total) {
    resultsDiv.textContent = `Mostrando ${count} de ${total} produtos`;
  } else {
    resultsDiv.textContent = '';
  }
}

function displayProducts(products) {
  const container = document.getElementById("products-container");
  if (!container) return;
  
  container.innerHTML = '';
  products.forEach(product => {
    const card = createProductCard(product);
    container.appendChild(card);
  });
  updateResultsCount(products.length, allProducts.length, currentSearchTerm);
}

function searchProducts(searchTerm, tag = null) {
  currentSearchTerm = searchTerm.trim();
  const clearBtn = document.getElementById('clearBtn');
  
  if (clearBtn) {
    if (currentSearchTerm) {
      clearBtn.classList.add('visible');
    } else {
      clearBtn.classList.remove('visible');
    }
  }
  
  if (currentSearchTerm) {
    // Busca no backend (mais eficiente para grandes volumes)
    let url = `/api/products?search=${encodeURIComponent(currentSearchTerm)}`;
    if (tag && tag !== 'all') {
      url += `&tag=${tag}`;
    }
    
    fetch(url, {
      headers: {
        "ngrok-skip-browser-warning": "true"
      }
    })
    .then(res => res.json())
    .then(products => {
      displayProducts(products);
    })
    .catch(err => {
      console.error("Erro ao buscar produtos:", err);
    });
  } else {
    // Se não há busca, mostra todos os produtos da tag atual
    if (tag && tag !== 'all') {
      fetch(`/api/products?tag=${tag}`, {
        headers: {
          "ngrok-skip-browser-warning": "true"
        }
      })
      .then(res => res.json())
      .then(products => {
        allProducts = products;
        displayProducts(products);
      })
      .catch(err => {
        console.error("Erro ao buscar produtos:", err);
      });
    } else {
      displayProducts(allProducts);
    }
  }
}

function clearSearch() {
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.value = '';
  }
  
  currentSearchTerm = '';
  const clearBtn = document.getElementById('clearBtn');
  if (clearBtn) {
    clearBtn.classList.remove('visible');
  }
  
  displayProducts(allProducts);
  if (searchInput) {
    searchInput.focus();
  }
}

// Inicializa a busca na página
function initializeSearch(tag = 'all') {
  const searchInput = document.getElementById('searchInput');
  if (!searchInput) return;
  
  // Debounce para evitar requisições excessivas
  let searchTimeout;
  searchInput.addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchProducts(e.target.value, tag);
    }, 300); // Aguarda 300ms após o usuário parar de digitar
  });

  // Busca ao pressionar Enter
  searchInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      clearTimeout(searchTimeout);
      searchProducts(e.target.value, tag);
    }
  });
}

// Função de ordenação global
function sortProducts(type) {
  // Remove active class de todos os botões
  document.querySelectorAll('.sort-btn').forEach(btn => btn.classList.remove('active'));
  
  // Adiciona active class ao botão clicado
  if (event && event.target) {
    event.target.classList.add('active');
  }

  // Pega os produtos atualmente exibidos
  const container = document.getElementById("products-container");
  const displayedProducts = Array.from(container.children).map(card => {
    const titleEl = card.querySelector('.title');
    const priceEl = card.querySelector('.price');
    
    return allProducts.find(p => 
      p.title === titleEl.innerText && 
      p.price === priceEl.innerText
    );
  }).filter(p => p); // Remove nulls

  let sortedProducts = [...displayedProducts];
  
  switch(type) {
    case 'price-asc':
      sortedProducts.sort((a, b) => getNumericPrice(a.price) - getNumericPrice(b.price));
      break;
    case 'price-desc':
      sortedProducts.sort((a, b) => getNumericPrice(b.price) - getNumericPrice(a.price));
      break;
    case 'discount':
      sortedProducts.sort((a, b) => getDiscountPercentage(b) - getDiscountPercentage(a));
      break;
  }
  
  // Limpa o container e adiciona produtos ordenados
  container.innerHTML = '';
  sortedProducts.forEach(product => {
    const card = createProductCard(product);
    container.appendChild(card);
  });
}
