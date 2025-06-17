// ✅ 광고 판별 기능의 활성화 여부를 나타내는 플래그 (기본값 true)
let isEnabled = true;

// ✅ 실제 블로그 URL 추출 함수
function extractBlogUrl(rawHref) {
  try {
    // 절대주소: blog.naver.com이면 그대로 사용
    if (rawHref.startsWith("https://blog.naver.com/") || rawHref.startsWith("http://blog.naver.com/")) {
      return rawHref;
    }

    // 상대주소 + u=... 포함 시 디코딩
    if (rawHref.startsWith("/")) {
      const dummyBase = "https://search.naver.com"; // 상대경로 보정용
      const fullUrl = new URL(rawHref, dummyBase);
      const encoded = fullUrl.searchParams.get("u");
      if (encoded) {
        const decoded = decodeURIComponent(encoded);
        if (decoded.startsWith("https://blog.naver.com/")) {
          return decoded;
        }
      }
    }

    return null;
  } catch (e) {
    console.warn("❌ URL 추출 실패:", rawHref);
    return null;
  }
}


// ✅ 블로그 링크들을 처리하는 함수
function processBlogLinks() {
  if (!isEnabled) return;
  if (!location.href.includes("ssc=tab.blog.all")) return;

  const blogLinks = document.querySelectorAll(".title_area a");

  blogLinks.forEach((link) => {
    if (!link.dataset.adChecked) {
      link.dataset.adChecked = "true";

      const emojiSpan = document.createElement("span");
      emojiSpan.textContent = "🔃 ";
      link.insertAdjacentElement("beforebegin", emojiSpan);

      let isVisible = true;
      const blinkInterval = setInterval(() => {
        emojiSpan.style.opacity = isVisible ? "0" : "1";
        isVisible = !isVisible;
      }, 1000);

      // ✅ url 정제 적용
      const actualUrl = extractBlogUrl(link.getAttribute("href"));
      if (!actualUrl) {
        clearInterval(blinkInterval);
        emojiSpan.textContent = "❔";
        return;
      }

      const checkAd = () => {
        chrome.runtime.sendMessage({ url: actualUrl }, (response) => {
          if (!response || response.result === 2) {
            console.log("응답 실패! 3초 후 재시도...");
            setTimeout(checkAd, 3000);
            return;
          }

          clearInterval(blinkInterval);
          const emoji = response.result === 1 ? "🚫 " : "✅";
          link.previousSibling.textContent = emoji;
          emojiSpan.style.opacity = 1;
        });
      };

      // 최종 호출
      checkAd();
    }
  });
}

// 🟩 1️⃣ 초기 상태 로딩 후 스크롤/DOM 변경 리스너 등록
chrome.storage.local.get(["isActive"], (result) => {
  // 저장된 상태를 불러와서 isEnabled에 반영
  isEnabled = result.isActive === undefined ? true : result.isActive;

  // 처음 로드될 때 광고 판별 수행
  if (isEnabled) processBlogLinks();

  // ✅ 초기화가 끝나면 스크롤 이벤트 리스너 등록
  let timer;
  window.addEventListener("scroll", () => {
    // 스크롤 이벤트 발생 시 300ms 동안 이벤트를 묶어서 처리 (디바운싱)
    clearTimeout(timer);
    timer = setTimeout(() => {
      processBlogLinks();
    }, 300);
  });

  // ✅ DOM에 새로운 요소가 추가되면 다시 광고 판별 수행
  const observer = new MutationObserver(() => {
    processBlogLinks();
  });
  observer.observe(document.body, { childList: true, subtree: true });
});

// 🟩 2️⃣ toggle 메시지 수신 처리 (아이콘 클릭 시 on/off 상태 변경 반영)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // toggle 메시지가 온다면 이 리스너 실행 활성화 여부를 갱신
  if (message.toggle !== undefined) {
    if (!location.href.includes("ssc=tab.blog.all")) return;

    isEnabled = message.toggle;
    if (isEnabled) {
      processBlogLinks();
    } else {
      // 비활성화된 경우, 기존에 삽입된 이모티콘 제거
      document.querySelectorAll(".title_area a").forEach((link) => {
        if (
          link.previousSibling &&
          (link.previousSibling.textContent === "✅ " ||
            link.previousSibling.textContent === "🚫 " ||
            link.previousSibling.textContent === "🔃 ")
        ) {
          link.previousSibling.remove();
        }
      });
    }
  }
});
