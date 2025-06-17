// DOMContentLoaded 이벤트: HTML 문서의 로드가 끝나면 아래 콜백 함수 실행
document.addEventListener("DOMContentLoaded", () => {
  // 토글 스위치 요소를 가져옴
  const toggleSwitch = document.getElementById("toggleSwitch");

  // 1️⃣ 저장된 상태 불러오기
  chrome.storage.local.get(["isActive"], (result) => {
    // 저장된 상태가 없으면 기본값을 true로 설정
    const isActive = result.isActive === undefined ? true : result.isActive;
    // 토글 스위치의 체크 상태를 저장된 상태로 맞춤
    toggleSwitch.checked = isActive;

    // 2️⃣ 아이콘 초기 상태 맞추기
    const iconPaths = {
      16: isActive ? "icons/16.png" : "icons/inactive_16.png",
      32: isActive ? "icons/32.png" : "icons/inactive_32.png",
      48: isActive ? "icons/48.png" : "icons/inactive_48.png",
      128: isActive ? "icons/128.png" : "icons/inactive_128.png",
    };
    // 확장 아이콘을 저장된 상태에 맞게 설정
    chrome.action.setIcon({ path: iconPaths });
  });

  // 3️⃣ 토글 버튼 변경 이벤트: 사용자 클릭 시
  toggleSwitch.addEventListener("change", () => {
    // 사용자가 선택한 상태 (true/false)
    const isActive = toggleSwitch.checked;

    // 3-1️⃣ 새로운 상태를 로컬 스토리지에 저장
    chrome.storage.local.set({ isActive });

    // 3-2️⃣ 아이콘을 새 상태에 맞게 즉시 변경
    const iconPaths = {
      16: isActive ? "icons/16.png" : "icons/inactive_16.png",
      32: isActive ? "icons/32.png" : "icons/inactive_32.png",
      48: isActive ? "icons/48.png" : "icons/inactive_48.png",
      128: isActive ? "icons/128.png" : "icons/inactive_128.png",
    };
    chrome.action.setIcon({ path: iconPaths });

    // 3-3️⃣ 현재 탭이 "네이버 검색의 블로그 탭"인지 확인
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0]; // 현재 활성화된 탭

      // 탭이 있고, url이 있고, 네이버 검색 & 블로그 탭인지 확인
      if (
        tab &&
        tab.url &&
        tab.url.includes("search.naver.com") &&
        tab.url.includes("ssc=tab.blog.all")
      ) {
        // ✅ 블로그 탭일 때만 content script로 상태 메시지를 보냄
        chrome.tabs.sendMessage(tab.id, { toggle: isActive });
      } else {
        // 블로그 탭이 아니면 로그를 출력
        console.log("현재 탭이 네이버 블로그 검색 결과가 아님!");
      }
    });
  });
});
