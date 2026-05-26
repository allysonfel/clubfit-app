let currentStep = 1;
const totalSteps = 44;

function nextStep(answer, field) {
    document.getElementById(`step-${currentStep}`).classList.add('hidden');
    currentStep++;
    document.getElementById(`step-${currentStep}`).classList.remove('hidden');
    updateBar();
}

function updateBar() {
    document.getElementById('bar').style.width = (currentStep / totalSteps * 100) + "%";
}

function toggleOption(el) {
    el.classList.toggle('selected-card'); // Crie essa classe no CSS com borda verde
}

function processBMI() {
    nextStep();
    // Simula o loading do Print 38
    let percent = 0;
    const interval = setInterval(() => {
        percent += 5;
        document.getElementById('loading-text').innerText = `Analisando perfil... ${percent}%`;
        if(percent >= 100) {
            clearInterval(interval);
            // Aqui você chamaria a tela de resultado (Próximo step)
        }
    }, 100);
}
