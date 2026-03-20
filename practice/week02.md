# Week 2 실습 기록

## 목표
pygame test 연습

## AI 대화 기록

**Q1: 더 예쁘게 만들어줘**

- AI 답변: glow_surface = pygame.Surface((60, 60), pygame.SRCALPHA) 사용

- 적용 결과: 글로우 효과가 생김.

**Q2: 이펙트가 동글동글한데 여러 도형이 나오게 만들어줘**

- AI 답변: self.shape = random.choice(["circle", "square", "triangle", "diamond", "star"])을 사용

- 시행착오: 도형 크기가 너무 작아 구별이 안가서 크기를 키우는 코드 부분을 알려달라함.

- 최종 해결: self.size = random.uniform(4, 10) 부분을 바꾸면 된다는 결론을 도출해서 크기를 키움.

**Q3 : 지금보니까 이펙트가 너무 많이 나와서 줄이고 싶어**

- AI 답변: for _ in range(숫자) 이 숫자를 줄이면 이펙트 개수가 줄어든다.

- 적용 결과: 이펙트 개수가 확실히 줄었다.

## 배운점
- 주어진 실습 코드를 내가 원하는 대로 AI를 활용하여 바꿔보았는데, AI가  이해하기 쉽게 설명도 잘 해주고 코드도 깔끔하게 줘서 AI활용이 중요하단 것을 배우게 되었다.