import { ref } from 'vue'
import { commandHistory } from '@/apps/slides/stores/historyMeta'

export function useDeferredCommit(getValue, buildCommand) {
	const valueOnStart = ref(null)

	const onStart = () => {
		valueOnStart.value = getValue()
	}

	const onEnd = () => {
		if (valueOnStart.value === null) return

		if (getValue() === valueOnStart.value) {
			// if value hasn't changed, just reset the valueOnStart for next time and return
			valueOnStart.value = null
			return
		}

		commandHistory.execute(buildCommand(valueOnStart.value, getValue()))
		valueOnStart.value = null
	}

	return { onStart, onEnd }
}
