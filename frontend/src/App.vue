<template>
  <main class="app-shell">
    <section class="welcome">
      <h1>图书管理员系统</h1>
      <p>基础项目结构已就绪，下一阶段可以开始实现登录、图书管理和借阅管理。</p>
    </section>
  </main>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f7f8fa;
  color: #1f2937;
  font-family:
    Inter,
    "Microsoft YaHei",
    sans-serif;
}

.welcome {
  width: min(720px, calc(100% - 48px));
}

.welcome h1 {
  margin: 0 0 16px;
  font-size: 36px;
  line-height: 1.2;
}

.welcome p {
  margin: 0;
  color: #4b5563;
  font-size: 16px;
  line-height: 1.7;
}
</style>
