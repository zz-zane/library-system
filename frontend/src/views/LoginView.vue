<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { extractErrorMessage } from '@/api/http'
import { isSafeRedirect } from '@/router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules: FormRules<typeof form> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleSubmit(): Promise<void> {
  if (formRef.value === undefined) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    await authStore.login({
      username: form.username.trim(),
      password: form.password
    })
    const redirect = route.query.redirect
    await router.replace(isSafeRedirect(redirect) ? redirect : '/books')
  } catch (error) {
    // 失败时保持用户名、清空密码
    form.password = ''
    ElMessage.error(extractErrorMessage(error))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <el-card class="login-card">
      <template #header>
        <h1 class="login-title">图书管理员系统</h1>
      </template>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            autocomplete="username"
            placeholder="请输入用户名"
            :disabled="submitting"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
            show-password
            :disabled="submitting"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-button
          class="login-button"
          type="primary"
          native-type="submit"
          :loading="submitting"
        >
          登录
        </el-button>
      </el-form>
    </el-card>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f7f8fa;
}

.login-card {
  width: min(400px, calc(100% - 48px));
}

.login-title {
  margin: 0;
  font-size: 20px;
  text-align: center;
  color: #1f2937;
}

.login-button {
  width: 100%;
}
</style>
