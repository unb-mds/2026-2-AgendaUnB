import { createClient } from '@supabase/supabase-js'
import { getSupabaseConfig } from './supabaseConfig.js'

const { url, key } = getSupabaseConfig(import.meta.env)
export const supabase = createClient(url, key)
