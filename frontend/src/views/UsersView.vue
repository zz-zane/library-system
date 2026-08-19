<script setup lang="ts">
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { extractErrorMessage } from '@/api/http'
import { createUserApi, listUsersApi, updateUserApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import type { UserOut, UserUpdate } from '@/types/user'

// 操作员管理页，契约见 docs/system-design.md 8.3 与 11.5
const authStore = useAuthStore()

const loading = ref(false)
const loadError = ref('')
const users = ref<UserOut[]>([])
const total = ref(0)

const query = reactive({
  page: 1,
  page_size: 20,
  username: '',
  is_active: '' as '' | boolean
})

async function loadUsers(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await listUsersApi({
      page: query.page,
      page_size: query.page_size,
      username: query.username.trim() || undefined,
      is_active: query.is_active === '' ? undefined : query.is_active
    })
    users.value = data.items
    total.value = data.total
  } catch (error) {
    users.value = []
    total.value = 0
    loadError.value = extractErrorMessage(error)
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  query.page = 1
  void loadUsers()
}

function handleReset(): void {
  query.username = ''
  query.is_active = ''
  query.page = 1
  void loadUsers()
}

function handlePageChange(page: number): void {
  query.page = page
  void loadUsers()
}

function handleSizeChange(size: number): void {
  query.page_size = size
  query.page = 1
  void loadUsers()
}

// 新增 / 编辑对话框
const dialogVisible = ref(false)
const dialogTitle = ref('')
const submitting = ref(false)
const editingUser = ref<UserOut | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: '',
  display_name: '',
  is_active: true
})

const USERNAME_PATTERN = /^[A-Za-z0-9_]{3,64}$/

const rules: FormRules<typeof form> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    {
      pattern: USERNAME_PATTERN,
      message: '用户名为 3-64 位字母、数字或下划线',
      trigger: 'blur'
    }
  ]
}

function openCreate(): void {
  editingUser.value = null
  dialogTitle.value = '新增操作员'
  Object.assign(form, { username: '', password: '', display_name: '', is_active: true })
  dialogVisible.value = true
}

function openEdit(user: UserOut): void {
  editingUser.value = user
  dialogTitle.value = `编辑操作员：${user.username}`
  Object.assign(form, {
    username: user.username,
    password: '',
    display_name: user.display_name ?? '',
    is_active: user.is_active
  })
  dialogVisible.value = true
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
    if (editingUser.value === null) {
      if (!form.password) {
        ElMessage.warning('请输入初始密码')
        return
      }
      await createUserApi({
        username: form.username.trim(),
        password: form.password,
        display_name: form.display_name.trim() || undefined
      })
      ElMessage.success('操作员创建成功')
    } else {
      const payload: UserUpdate = {}
      const displayName = form.display_name.trim()
      if (displayName !== (editingUser.value.display_name ?? '')) {
        payload.display_name = displayName
      }
      if (form.password) {
        payload.password = form.password
      }
      if (form.is_active !== editingUser.value.is_active) {
        payload.is_active = form.is_active
      }
      if (Object.keys(payload).length === 0) {
        ElMessage.info('没有需要保存的变更')
        dialogVisible.value = false
        return
      }
      await updateUserApi(editingUser.value.id, payload)
      ElMessage.success('操作员更新成功')
    }
    dialogVisible.value = false
    await loadUsers()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

onMounted(loadUsers)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h2>操作员管理</h2>
      <el-button type="primary" @click="openCreate">新增操作员</el-button>
    </div>

    <el-form class="filter-bar" inline @submit.prevent="handleSearch">
      <el-form-item label="用户名">
        <el-input
          v-model="query.username"
          placeholder="用户名"
          clearable
          style="width: 180px"
          @clear="handleSearch"
        />
      </el-form-item>
      <el-form-item label="状态">
        <el-select
          v-model="query.is_active"
          placeholder="全部"
          clearable
          style="width: 120px"
          @change="handleSearch"
        >
          <el-option label="启用" :value="true" />
          <el-option label="停用" :value="false" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="users" stripe>
      <el-table-column prop="username" label="用户名" min-width="140" />
      <el-table-column label="展示名" min-width="140">
        <template #default="{ row }">{{ row.display_name ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty :description="loadError || '暂无操作员数据'" />
      </template>
    </el-table>

    <el-pagination
      class="pagination"
      background
      layout="total, sizes, prev, pager, next"
      :total="total"
      :current-page="query.page"
      :page-size="query.page_size"
      :page-sizes="[10, 20, 50]"
      @current-change="handlePageChange"
      @size-change="handleSizeChange"
    />

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            maxlength="64"
            :disabled="editingUser !== null"
            placeholder="3-64 位字母、数字或下划线"
          />
        </el-form-item>
        <el-form-item :label="editingUser === null ? '初始密码' : '重置密码'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editingUser === null ? '必填' : '留空则不修改'"
          />
        </el-form-item>
        <el-form-item label="展示名">
          <el-input v-model="form.display_name" maxlength="64" placeholder="选填" />
        </el-form-item>
        <el-form-item v-if="editingUser !== null" label="启用状态">
          <el-switch
            v-model="form.is_active"
            :disabled="editingUser.id === authStore.user?.id"
          />
          <span
            v-if="editingUser.id === authStore.user?.id"
            class="self-hint"
          >
            不能停用当前登录账号
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          保存
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.page {
  padding: 24px;
  background: #fff;
  border-radius: 8px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
}

.filter-bar {
  margin-bottom: 8px;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.self-hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
