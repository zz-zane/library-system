<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import {
  createBookApi,
  deleteBookApi,
  listBooksApi,
  updateBookApi
} from '@/api/books'
import { extractErrorMessage } from '@/api/http'
import type { BookOut } from '@/types/book'

// 图书管理页，契约见 docs/system-design.md 8.4 与 11.5
const loading = ref(false)
const loadError = ref('')
const books = ref<BookOut[]>([])
const total = ref(0)

const query = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  category: '',
  available_only: false
})

async function loadBooks(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await listBooksApi({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword.trim() || undefined,
      category: query.category.trim() || undefined,
      available_only: query.available_only || undefined
    })
    books.value = data.items
    total.value = data.total
  } catch (error) {
    books.value = []
    total.value = 0
    loadError.value = extractErrorMessage(error)
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  query.page = 1
  void loadBooks()
}

function handleReset(): void {
  query.keyword = ''
  query.category = ''
  query.available_only = false
  query.page = 1
  void loadBooks()
}

function handlePageChange(page: number): void {
  query.page = page
  void loadBooks()
}

function handleSizeChange(size: number): void {
  query.page_size = size
  query.page = 1
  void loadBooks()
}

// 新增 / 编辑对话框
const dialogVisible = ref(false)
const dialogTitle = ref('')
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  title: '',
  author: '',
  isbn: '',
  publisher: '',
  publish_year: undefined as number | undefined,
  category: '',
  total_copies: 1,
  description: ''
})

const rules: FormRules<typeof form> = {
  title: [
    { required: true, message: '请输入书名', trigger: 'blur' },
    { max: 200, message: '书名不能超过 200 字', trigger: 'blur' }
  ],
  author: [
    { required: true, message: '请输入作者', trigger: 'blur' },
    { max: 100, message: '作者不能超过 100 字', trigger: 'blur' }
  ],
  isbn: [{ max: 20, message: 'ISBN 不能超过 20 字', trigger: 'blur' }],
  total_copies: [{ required: true, message: '请输入总库存', trigger: 'blur' }]
}

function openCreate(): void {
  editingId.value = null
  dialogTitle.value = '新增图书'
  Object.assign(form, {
    title: '',
    author: '',
    isbn: '',
    publisher: '',
    publish_year: undefined,
    category: '',
    total_copies: 1,
    description: ''
  })
  dialogVisible.value = true
}

function openEdit(book: BookOut): void {
  editingId.value = book.id
  dialogTitle.value = '编辑图书'
  Object.assign(form, {
    title: book.title,
    author: book.author,
    isbn: book.isbn ?? '',
    publisher: book.publisher ?? '',
    publish_year: book.publish_year ?? undefined,
    category: book.category ?? '',
    total_copies: book.total_copies,
    description: book.description ?? ''
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

  const payload = {
    title: form.title.trim(),
    author: form.author.trim(),
    isbn: form.isbn.trim() || undefined,
    publisher: form.publisher.trim() || undefined,
    publish_year: form.publish_year ?? undefined,
    category: form.category.trim() || undefined,
    total_copies: form.total_copies,
    description: form.description.trim() || undefined
  }

  submitting.value = true
  try {
    if (editingId.value === null) {
      await createBookApi(payload)
      ElMessage.success('图书创建成功')
    } else {
      await updateBookApi(editingId.value, payload)
      ElMessage.success('图书更新成功')
    }
    dialogVisible.value = false
    await loadBooks()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(book: BookOut): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除图书《${book.title}》吗？存在借阅历史时将被拒绝。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await deleteBookApi(book.id)
    ElMessage.success('图书已删除')
    // 删除后当前页可能为空，回退一页
    if (books.value.length === 1 && query.page > 1) {
      query.page -= 1
    }
    await loadBooks()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  }
}

onMounted(loadBooks)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h2>图书管理</h2>
      <el-button type="primary" @click="openCreate">新增图书</el-button>
    </div>

    <el-form class="filter-bar" inline @submit.prevent="handleSearch">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          placeholder="书名 / 作者 / ISBN"
          clearable
          style="width: 220px"
          @clear="handleSearch"
        />
      </el-form-item>
      <el-form-item label="分类">
        <el-input
          v-model="query.category"
          placeholder="分类"
          clearable
          style="width: 140px"
          @clear="handleSearch"
        />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="query.available_only" @change="handleSearch">
          仅看可借
        </el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="books" stripe>
      <el-table-column prop="title" label="书名" min-width="180" show-overflow-tooltip />
      <el-table-column prop="author" label="作者" min-width="120" show-overflow-tooltip />
      <el-table-column prop="isbn" label="ISBN" min-width="140">
        <template #default="{ row }">{{ row.isbn ?? '—' }}</template>
      </el-table-column>
      <el-table-column prop="category" label="分类" width="110">
        <template #default="{ row }">{{ row.category ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="库存" width="120">
        <template #default="{ row }">
          {{ row.available_copies }} / {{ row.total_copies }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty :description="loadError || '暂无图书数据'" />
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
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="书名" prop="title">
          <el-input v-model="form.title" maxlength="200" />
        </el-form-item>
        <el-form-item label="作者" prop="author">
          <el-input v-model="form.author" maxlength="100" />
        </el-form-item>
        <el-form-item label="ISBN" prop="isbn">
          <el-input v-model="form.isbn" maxlength="20" placeholder="选填，ISBN-10 或 ISBN-13" />
        </el-form-item>
        <el-form-item label="出版社">
          <el-input v-model="form.publisher" maxlength="200" placeholder="选填" />
        </el-form-item>
        <el-form-item label="出版年份">
          <el-input-number
            v-model="form.publish_year"
            :min="1000"
            :max="2100"
            placeholder="选填"
            style="width: 160px"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" maxlength="50" placeholder="选填" />
        </el-form-item>
        <el-form-item label="总库存" prop="total_copies">
          <el-input-number v-model="form.total_copies" :min="1" :max="999" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="2000"
            placeholder="选填"
          />
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
</style>
