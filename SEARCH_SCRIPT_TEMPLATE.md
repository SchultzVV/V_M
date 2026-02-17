// Script de busca para copiar e colar nas seções
// Adicionar após a declaração de allProducts

let currentSearchTerm = ''; // Termo de busca atual

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
  const container = document.getElementById('products-container');
  if (!container) return;
  
  container.innerHTML = '';
  if (products.length === 0) {
    container.innerHTML = '<p style="text-align: center; color: #666; font-size: 18px; margin-top: 40px;">Nenhum produto encontrado 😢</p>';
  } else {
    products.forEach(product => {
      const card = createProductCard(product);
      container.appendChild(card);
    });
  }
  updateResultsCount(products.length, allProducts.length, currentSearchTerm);
}

function searchProducts(searchTerm, tag) {
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
    fetch(`/api/products?tag=${tag}&search=${encodeURIComponent(currentSearchTerm)}`, {
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
    // Se não há busca, mostra todos os produtos da tag
    displayProducts(allProducts);
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

// Event listeners para a busca (adicionar após o fetch de produtos)
const searchInput = document.getElementById('searchInput');
if (searchInput) {
  let searchTimeout;
  searchInput.addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchProducts(e.target.value, 'TAG_AQUI'); // Substituir TAG_AQUI pela tag correta
    }, 300);
  });

  searchInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      clearTimeout(searchTimeout);
      searchProducts(e.target.value, 'TAG_AQUI'); // Substituir TAG_AQUI pela tag correta
    }
  });
}
