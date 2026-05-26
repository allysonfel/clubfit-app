// Controle de Estados do Quiz
let currentStep = 1;
const totalSteps = 44; // Total de telas que vamos montar
let userData = {
    ageRange: '',
    goals: [],
    height: 0,
    weight: 0,
    bmi: 0
};

/**
 * Função para avançar de tela
 * @param {string} answer - A resposta escolhida
 * @param {string} field - O campo no objeto userData
 */
function nextStep(answer = null, field = null) {
    // Se houver uma resposta única, salva no objeto
    if (field && answer) {
        userData[field] = answer;
    }

    // Esconde a tela atual com uma pequena transição (opcional)
    const currentScreen = document.getElementById(`step-${currentStep}`);
    if (currentScreen) {
        currentScreen.classList.add('hidden');
    }
    
    // Avança o contador
    currentStep++;
    
    // Mostra a próxima tela
    const nextScreen = document.getElementById(`step-${currentStep}`);
    if (nextScreen) {
        nextScreen.classList.remove('hidden');
        window.scrollTo(0, 0); // Volta pro topo da tela
    }

    // Atualiza a barra de progresso
    updateProgressBar();
}

/**
 * Atualiza visualmente a barra de progresso no topo
 */
function updateProgressBar() {
    const bar = document.getElementById('bar');
    const percentage = (currentStep / totalSteps) * 100;
    bar.style.width = percentage + "%";
}

/**
 * Lógica específica para telas de múltipla escolha (Objetivos)
 */
function toggleOption(element, value) {
    element.classList.toggle('selected');
    // Aqui você poderia adicionar o valor a um array se quiser processar depois
}

/**
 * Cálculo de IMC e Perfil de Peso
 */
function calculateBMI() {
    const height = document.getElementById('height').value;
    const weight = document.getElementById('weight').value;

    if (!height || !weight || height < 50 || weight < 20) {
        alert("Por favor, insira valores válidos para altura e peso.");
        return;
    }

    // Cálculo: peso / (altura em metros)²
    const heightInMeters = height / 100;
    const bmiResult = (weight / (heightInMeters * heightInMeters)).toFixed(1);
    
    userData.height = height;
    userData.weight = weight;
    userData.bmi = bmiResult;

    // Injeta o valor na tela de resultados antes de mostrar
    const bmiDisplay = document.getElementById('bmi-value');
    if (bmiDisplay) {
        bmiDisplay.innerText = bmiResult;
    }

    nextStep();
}

// Inicializa a barra no começo
updateProgressBar();