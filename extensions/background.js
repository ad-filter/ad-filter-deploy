// ✅ 백그라운드에서 content.js의 메시지를 수신
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // 만약 message에 'url' 속성이 있으면 (즉, 광고 여부 확인 요청)
  if (message.url) {
    // 서버로 POST 요청: 광고 여부를 판별
    fetch("http://localhost:8000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" }, // JSON 데이터 전송
      body: JSON.stringify({ url: message.url }), // 전송할 데이터 (url)
    })
      // 서버 응답을 JSON으로 파싱
      .then((res) => res.json())
      // 파싱된 데이터의 result를 content.js로 응답 전송
      .then((data) => {
        if (data.is_ad === true) {
          sendResponse({ result: 1 }); // ✅ 광고
        } else if (data.is_ad === false) {
          sendResponse({ result: 0 }); // ✅ 일반
        } else {
          sendResponse({ result: 2 }); // ❌ 판별 실패 → 재시도
        }
      })
      .catch((error) => {
        console.error("요청 오류:", error);
        sendResponse({ result: 2 }); // ❌ 오류 → 재시도
      });

    // ✅ 비동기 처리임을 명시 (sendResponse를 비동기로 사용할 때 필요)
    return true;
  }
});

// ✅ 확장 프로그램의 아이콘을 저장된 상태(isActive)에 맞게 초기화
function updateIcon() {
  // 로컬 스토리지에서 isActive 상태를 불러오기
  chrome.storage.local.get(["isActive"], (result) => {
    // 저장된 상태가 없으면 true, 있으면 그대로 사용
    const isActive = result.isActive === undefined ? true : result.isActive;
    // 상태에 따라 아이콘 경로를 결정
    const iconPaths = {
      16: isActive ? "icons/16.png" : "icons/inactive_16.png",
      32: isActive ? "icons/32.png" : "icons/inactive_32.png",
      48: isActive ? "icons/48.png" : "icons/inactive_48.png",
      128: isActive ? "icons/128.png" : "icons/inactive_128.png",
    };
    // 아이콘 변경
    chrome.action.setIcon({ path: iconPaths });
  });
}

// ✅ 크롬이 시작될 때 아이콘 초기화
chrome.runtime.onStartup.addListener(updateIcon);

// ✅ 확장 프로그램이 설치되거나 업데이트될 때 아이콘 초기화
chrome.runtime.onInstalled.addListener(updateIcon);
