# 1:1 Chat Web Application

본 프로젝트는 **1:1 채팅 웹 애플리케이션**으로,  
정확한 구현보다는 **설계 방향과 작업 스타일**을 보여주는 것을 목표로 제작되었습니다.

---

## 기술 스택
- Backend: Django, Django REST Framework
- Frontend: HTML, CSS, Vanilla JavaScript
- Database: SQLite (과제/로컬 실행 목적)
- Auth: Django Session 기반 인증

---

## 주요 기능
- 1:1 대화방 생성 및 이동
- 메시지 전송/조회 및 서버 저장
- 대화방별 메시지 분리
- 읽음/안읽음 처리
- 사용자 검색을 통한 새 대화 생성
- URL 자동 링크 처리
- 안 읽은 메시지 수 표시

---

## 설계 요약
- **View는 얇게, Serializer는 두껍게** 구성하여  
  입력값 검증과 비즈니스 로직을 Serializer에서 처리
- 1:1 대화방 중복 생성을 방지하여 데이터 정합성 유지
- ConversationMember 모델로 사용자별 읽음 상태 관리
- 프론트엔드는 Vanilla JS로 최소 SPA 형태 구현
- 메시지 중복 전송 방지를 위한 client-side lock 적용

---

## 실시간 처리
- 기본 구현은 **폴링 방식** (2.5초)
- Django Channels 기반 **WebSocket으로 확장 가능한 구조**

---

## 더미 사용자 생성 커맨드
로컬 개발 및 테스트를 위해 더미 사용자 생성 커맨드를 제공합니다.
- python manage.py seed_users
- 기본 동작:
	•	user1 ~ user5 생성
	•	기본 비밀번호: pass1234

---

## 실행 방법
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
