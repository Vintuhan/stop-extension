"use strict";

// Свои фразы можно добавлять сюда, по одной в кавычках через запятую.
const QUOTES = [
  "Азарт обещает выигрыш, а на деле забирает время, деньги и покой.",
  "В долгой игре выигрывает казино. Всегда.",
  "Желание сыграть накатывает волной и отступает, если его переждать.",
  "Через час вы будете рады, что закрыли эту вкладку.",
  "Отыграться нельзя. Остановиться можно.",
  "Самое сложное вы уже сделали: остановились.",
];

document.getElementById("quote").textContent =
  QUOTES[Math.floor(Math.random() * QUOTES.length)];

// Подсказка «вдох / выдох» в такт кольцу (4 секунды на каждое)
const hint = document.getElementById("hint");
let inhale = true;
setInterval(() => {
  inhale = !inhale;
  hint.textContent = inhale ? "Вдох" : "Выдох";
}, 4000);

document.getElementById("close").addEventListener("click", () => {
  try {
    chrome.tabs.getCurrent((tab) => {
      if (tab && tab.id !== undefined) chrome.tabs.remove(tab.id);
      else window.close();
    });
  } catch (e) {
    window.close();
  }
});
