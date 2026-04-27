import { ref } from 'vue'
import { commandHistory } from '@/stores/historyMeta'

export function useDeferredCommit(getValue, buildCommand) {
	const valueOnStart = ref(null)

	const onStart = () => {
		valueOnStart.value = getValue()
	}

	const onEnd = () => {
		if (getValue() === valueOnStart.value) return
		commandHistory.execute(buildCommand(valueOnStart.value, getValue()))
		valueOnStart.value = null
	}

	return { onStart, onEnd }
}
